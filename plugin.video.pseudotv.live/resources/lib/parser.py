#   Copyright (C) 2022 Lunatixz
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
from resources.lib.fileaccess  import FileLock
from resources.lib.cache       import Cache
from resources.lib.channels    import Channels
from resources.lib.jsonrpc     import JSONRPC 
from resources.lib.backup      import Backup
from resources.lib.builder     import Builder 
from resources.lib.m3u         import M3U
from resources.lib.xml         import XMLTV
from resources.lib.rules       import RulesList
from resources.lib.library     import Library

class Writer:
    globalFileLock = FileLock()
    
    def __init__(self, service=None):
        if service is None:
            from resources.lib.vault import Vault
            self.vault     = Vault()
            self.monitor   = xbmc.Monitor()
            self.player    = xbmc.Player()
        else:
            self.vault     = service.vault
            self.monitor   = service.monitor
            self.player    = service.player
        
        self.rules         = RulesList()
        self.cache         = Cache()
        self.dialog        = Dialog()
        self.jsonRPC       = JSONRPC(inherited=self)
        
        self.channels      = Channels(writer=self)
        self.library       = Library(writer=self)
        self.recommended   = self.library.recommended
        
        self.builder       = Builder(writer=self)
        self.m3u           = M3U(writer=self)
        self.xmltv         = XMLTV(writer=self)
        self.backup        = Backup(writer=self)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def addChannelLineup(self, citem, radio=False, catchup=True):
        citem['label'] = (citem.get('label','') or citem['name'])
        citem['url']   = PVR_URL.format(addon=ADDON_ID,name=quoteString(citem['name']),id=quoteString(citem['id']),radio=str(citem['radio']))
        
        if not SETTINGS.getSettingBool('Enable_Grouping'): 
            citem['group'] = [ADDON_NAME]
        else:
            if ADDON_NAME not in citem['group']:
                citem['group'].append(ADDON_NAME)
                
            if citem.get('favorite',False):
                 if not LANGUAGE(30201) in citem['group']: 
                    citem['group'].append(LANGUAGE(30201))
            else:
                 if LANGUAGE(30201) in citem['group']: 
                     citem['group'].remove(LANGUAGE(30201))
        citem['group'] = list(set(citem['group']))
        
        self.log('addChannelLineup, citem = %s, radio = %s, catchup = %s'%(citem,radio,catchup))
        self.m3u.addStation(citem)
        self.xmltv.addChannel(citem)
    

    def addProgrammes(self, citem, fileList, radio=False, catchup=True):
        self.log('addProgrammes, radio = %s, catchup = %s, programmes = %s, citem = %s'%(radio,catchup,len(fileList),citem))
        for idx, file in enumerate(fileList):
            item = {}
            item['radio']       = radio
            item['channel']     = citem['id']
            item['start']       = file['start']
            item['stop']        = file['stop']
            item['title']       = file['label']
            item['desc']        = file['plot']
            item['length']      = file['duration']
            item['sub-title']   = (file.get('episodetitle','') or '')
            item['categories']  = (file.get('genre','')        or ['Undefined'])[:5]
            item['type']        = file.get('type','video')
            item['new']         = int(file.get('playcount','1')) == 0
            item['thumb']       = getThumb(file,SETTINGS.getSettingInt('EPG_Artwork'))
            file['art']['thumb']= getThumb(file,{0:1,1:0}[SETTINGS.getSettingInt('EPG_Artwork')]) #unify thumbnail artwork, opposite of EPG_Artwork
            item['date']        = file.get('premiered','')
            
            if catchup:
                item['catchup-id'] = VOD_URL.format(addon=ADDON_ID,name=quoteString(item['title']),id=quoteString(encodeString((file.get('originalfile','') or file.get('file','')))),channel=quoteString(citem['id']),radio=str(item['radio']))
                file['catchup-id'] = item['catchup-id']
                
            if (item['type'] != 'movie' and ((file.get("season",0) > 0) and (file.get("episode",0) > 0))):
                item['episode-num'] = {'xmltv_ns':'%s.%s'%(file.get("season",1)-1,file.get("episode",1)-1),
                                       'onscreen':'S%sE%s'%(str(file.get("season",0)).zfill(2),str(file.get("episode",0)).zfill(2))}

            item['rating']      = cleanMPAA(file.get('mpaa','') or 'NA')
            item['stars']       = (file.get('rating','')        or '0')
            item['writer']      = ', '.join(file.get('writer',[])[:5])
            item['director']    = file.get('director',[])[:5]
            item['actor']       = ['%s - %s'%(actor.get('name'),actor.get('role','')) for actor in file.get('cast',[])[:5] if actor.get('name')]

            file['citem']       = citem #channel item (stale data due to xmltv storage) use for reference.
            item['fitem']       = file  #raw kodi fileitem/listitem, contains citem both passed through 'writer' xmltv param.
            
            streamdetails = file.get('streamdetails',{})
            if streamdetails:
                item['subtitle'] = list(set([sub.get('language','') for sub in streamdetails.get('subtitle',[]) if sub.get('language')]))
                item['language'] = ', '.join(list(set([aud.get('language','') for aud in streamdetails.get('audio',[]) if aud.get('language')])))
                item['audio']    = True if True in list(set([aud.get('codec','') for aud in streamdetails.get('audio',[]) if aud.get('channels',0) >= 2])) else False
                item.setdefault('video',{})['aspect'] = list(set([vid.get('aspect','') for vid in streamdetails.get('video',[]) if vid.get('aspect','')]))
            self.xmltv.addProgram(citem['id'], item)
            

    def removeChannelLineup(self, citem): #clean channel from m3u/xmltv
        self.log('removeChannelLineup, citem = %s'%(citem))
        self.m3u.removeStation(citem)
        self.xmltv.removeBroadcasts(citem)
        
        
    def cleanChannelLineup(self):
        # Clean M3U/XMLTV from abandoned channels.
        channels    = self.channels.getChannels()
        m3uChannels = self.m3u.getStations()
        abandoned   = m3uChannels.copy() 
        
        if (channels or m3uChannels) is None: return True
        [abandoned.remove(m3u) for channel in channels for m3u in m3uChannels if channel.get('id') == m3u.get('id')]
        if abandoned != m3uChannels:
            self.log('cleanChannelLineup, abandoned from M3U = %s'%(len(abandoned)))
            for leftover in abandoned:
                self.removeChannelLineup(leftover)
                if self.builder.pDialog is not None:
                    self.builder.pCount += .1
                    self.builder.pDialog = self.dialog.progressBGDialog(self.builder.pCount, self.builder.pDialog, message=leftover.get('name'),header='%s, %s'%(ADDON_NAME,LANGUAGE(30327)))
                    self.monitor.waitForAbort((PROMPT_DELAY/2)/1000)
        return True
 

    def saveChannelLineup(self):
        self.log('saveChannelLineup')
        if self.cleanChannelLineup() and self.importSETS():
            if False in [self.m3u._save(), self.xmltv._save()]:
                self.dialog.notificationDialog(LANGUAGE(30001))
                return False
        return True
        

    def importSETS(self):
        self.log('importSETS')
        importLST = self.channels.getImports()
        
        if SETTINGS.getSettingBool('User_Import'): #append user third-party m3u/xmltv to recommended import list.
            Import_M3U_Path   = {0:SETTINGS.getSetting('Import_M3U_FILE'),
                                 1:SETTINGS.getSetting('Import_M3U_URL')}[SETTINGS.getSettingInt('Import_M3U_TYPE')]
                                 
            Import_XMLTV_Path = {0:SETTINGS.getSetting('Import_XMLTV_FILE'),
                                 1:SETTINGS.getSetting('Import_XMLTV_URL'),
                                 2:SETTINGS.getSetting('Import_XMLTV_M3U')}[SETTINGS.getSettingInt('Import_XMLTV_TYPE')]

            importLST.append({'item':{'type':'iptv','name':'Third-Party M3U/XMLTV',
                                      'm3u':{'path':Import_M3U_Path,'providers':SETTINGS.getSettingList('Import_Provider')},
                                      'xmltv':{'path':Import_XMLTV_Path}}})
        
        for idx, item in enumerate(importLST):
            try:
                importItem = item.get('item',{})
                if importItem.get('type','') != 'iptv': continue
                self.log('importSETS, %s: importItem = %s'%(idx,importItem))
                
                idx += 1
                m3ufle   = importItem.get('m3u'  ,{}).get('path','')
                xmlfle   = importItem.get('xmltv',{}).get('path','')
                filters  = {'slug'     :importItem.get('m3u',{}).get('slug',''),
                            'providers':importItem.get('m3u',{}).get('provider',[])}
                            
                self.xmltv.importXMLTV(xmlfle,self.m3u.importM3U(m3ufle,filters,multiplier=idx))
                if self.builder.pDialog is not None:
                    self.builder.pCount += .1
                    self.builder.pDialog = self.dialog.progressBGDialog(self.builder.pCount, self.builder.pDialog, message=importItem.get('name'),header='%s, %s'%(ADDON_NAME,LANGUAGE(30151)))
                    self.monitor.waitForAbort((PROMPT_DELAY/2)/1000)
            except Exception as e: self.log("importSETS, Failed! %s"%(e), xbmc.LOGERROR)
        return True


    def findChannel(self, citem, channels=[]):
        for idx, eitem in enumerate(channels):
            if (citem.get('id') == eitem.get('id',str(random.random()))) or (citem.get('type','').lower() == eitem.get('type',str(random.random())).lower() and citem.get('name','').lower() == eitem.get('name',str(random.random())).lower()):
                self.log('findChannel, found citem = %s'%(citem))
                return idx, eitem
        return None, {}
        

    def autoTune(self):
        if hasAutotuned() or isClient(): return True#already ran or dismissed by user, check on next reboot.
        elif self.backup.hasBackup():
            retval = self.dialog.yesnoDialog(LANGUAGE(30132)%(ADDON_NAME,LANGUAGE(30287)), yeslabel=LANGUAGE(30203),customlabel=LANGUAGE(30211),autoclose=90000)
            if   retval == 2: return self.recoverChannelsFromBackup()
            elif retval != 1: return True
        else:
            if not self.dialog.yesnoDialog(LANGUAGE(30132)%(ADDON_NAME,LANGUAGE(30286)),autoclose=90000): 
                return False
       
        types = CHAN_TYPES.copy()
        types.remove(LANGUAGE(30033)) #exclude Imports from auto tuning. ie. Recommended Services
        pDialog = self.dialog.progressBGDialog()
        for idx, type in enumerate(types):
            self.log('autoTune, type = %s'%(type))
            pDialog = self.dialog.progressBGDialog((idx*100//len(types)), pDialog, type, header='%s, %s'%(ADDON_NAME,LANGUAGE(30102)))
            self.selectPredefined(type,AUTOTUNE_LIMIT)
        self.dialog.progressBGDialog(100, pDialog, '%s...'%(LANGUAGE(30053)))
        return True


    def selectPredefined(self, type=None, autoTune=None):
        self.log('selectPredefined, type = %s, autoTune = %s'%(type,autoTune))
        if isClient(): return self.dialog.notificationDialog(LANGUAGE(30288))
        with busy_dialog():
            items = self.library.getLibraryItems(type)
            if not items:
                self.dialog.notificationDialog(LANGUAGE(30103)%(type))
                return
                
            listItems = poolit(self.library.buildLibraryListitem)(items,type)
            if autoTune:
                if autoTune > len(items): autoTune = len(items)
                select = random.sample(list(set(range(0,len(items)))),autoTune)
                
        if not autoTune:
            select = self.dialog.selectDialog(listItems,LANGUAGE(30272)%(type),preselect=list(self.matchLizIDX(listItems,self.library.getEnabledItems(items))))
            
        if not select is None:
            with busy_dialog():
                self.library.setEnableStates(type,list(self.matchDictIDX(items,[listItems[idx] for idx in select])),items)
                self.buildPredefinedChannels(type)
                setUpdatePending()


    def matchLizIDX(self, listitems, selects, key='name', retval=False):
        for select in selects:
            for idx, listitem in enumerate(listitems):
                if select.get(key) == listitem.getLabel():
                    if retval: yield listitem
                    else:      yield idx


    def matchDictIDX(self, items, listitems, key='name', retval=False):
        for listitem in listitems:
            for idx, item in enumerate(items):
                if listitem.getLabel() == item.get(key):
                    if retval: yield item
                    else:      yield idx

    
    # #### #update pre-defined channels, meta maybe dynamic parse for change.
    # #### elif item['number'] >= CHANNEL_LIMIT:
    # #### item['logo'] = (self.jsonRPC.resources.getLogo(channel['name'],channel['type'],channel['path'],channel, featured=True, lookup=True) or channel.get('logo',LOGO))
    # #### item['path'] = self.library.predefined.pathTypes[channel['type']](cleanChannelSuffix(channel['name']))
    
            
    def buildPredefinedChannels(self, type=None):
        if not type is None: types = [type]
        else:                types = CHAN_TYPES
        self.log('buildPredefinedChannels, types = %s'%(types))
        
        # convert enabled library.json into channels.json items
        def buildAvailableRange(enumbers):
            # create number array for given type, excluding existing channel numbers.
            start = ((CHANNEL_LIMIT+1)*(CHAN_TYPES.index(type)+1))
            stop  = (start + CHANNEL_LIMIT)
            self.log('buildPredefinedChannels, type = %s, range = %s-%s, enumbers = %s'%(type,start,stop,enumbers))
            return [num for num in range(start,stop) if num not in enumbers]
                    
        for type in types:
            if self.monitor.waitForAbort(0.001) or self.monitor.isSettingsOpened(): 
                self.log('buildPredefinedChannels, interrupted')
                return
                
            items = self.library.getLibraryItems(type, enabled=True)
            self.log('buildPredefinedChannels, type = %s, enabled items = %s'%(type,len(items)))

            if type == LANGUAGE(30033): #convert enabled imports to channel items.
                self.channels.setImports(items)
            else:
                echannels = self.channels.getPredefinedChannelsByType(type) # existing channels, avoid duplicates, aid in removal.
                enumbers  = [echannel.get('number') for echannel in echannels if echannel.get('number',0) > 0] # existing channel numbers
                numbers   = iter(buildAvailableRange(enumbers)) #list of available channel numbers
                addLST    = []
                removeLST = echannels.copy()

                for item in items:
                    if self.monitor.waitForAbort(0.001) or self.monitor.isSettingsOpened(): 
                        self.log('buildPredefinedChannels, interrupted')
                        return
                        
                    citem = self.channels.getCitem()
                    citem.update({'name'     :getChannelSuffix(item['name'], type),
                                  'path'     :item['path'],
                                  'type'     :item['type'],
                                  'logo'     :item['logo'],
                                  'group'    :[type]})
                                  
                    citem['group']   = list(set(citem['group']))
                    citem['radio']   = (item['type'] == LANGUAGE(30097) or 'musicdb://' in item['path'])
                    citem['catchup'] = ('vod' if not citem['radio'] else '')
                    
                    match, eitem = self.findChannel(citem,echannels)
                    if match is None:#add new channel
                        citem['number'] = next(numbers,0)
                        citem['id']     = getChannelID(citem['name'],citem['path'],citem['number'])
                    else:#update new citems with existing values.
                        if eitem in removeLST: removeLST.remove(eitem)
                        for key in ['id','rules','number','favorite']: 
                            if eitem.get(key):
                                citem[key] = eitem[key] #transfer static channels values.
                    addLST.append(citem)
                
                if len(addLST) > 0 and (addLST != removeLST):
                    difference = sorted(diffLSTDICT(removeLST,addLST), key=lambda k: k['number'])
                    for citem in difference: #add new, remove old.
                        if   citem.get('number',0) < CHANNEL_LIMIT: continue #unnecessary check to enforce only changes to predefined channels.
                        elif citem in addLST: self.channels.addChannel(citem)
                        else:                 self.channels.removeChannel(citem)
                            
        self.log('buildPredefinedChannels, finished building')
        return self.channels._save()

        
    def recoverChannelsFromBackup(self, file=CHANNELFLE_BACKUP):
        newChannels = self.vault._load(CHANNELFLE_BACKUP).get('channels',[])
        difference  = sorted(diffLSTDICT(self.channels.getChannels(),newChannels), key=lambda k: k['number'])
        self.log('recoverChannelsFromBackup, file = %s, difference = %s'%(file,len(difference)))
        
        if len(difference) > 0:
            pDialog = self.dialog.progressDialog(message=LANGUAGE(30338))

            for idx, citem in enumerate(difference):
                pCount = int(((idx + 1)*100)//len(difference))
                if citem in newChannels: 
                    pDialog = self.dialog.progressDialog(pCount,pDialog,message="%s: %s"%(LANGUAGE(30338),citem.get('name')),header='%s, %s'%(ADDON_NAME,LANGUAGE(30338)))
                    self.channels.addChannel(citem)
                else: 
                    self.channels.removeChannel(citem)
            setRestartRequired(self.channels._save())
        return True


    def clearChannels(self, type='all'): #clear user-defined channels. all includes pre-defined
        self.log('clearChannels, type = %s'%(type))
        channels = {'all'          : self.channels.getChannels,
                    'user-defined' : self.channels.getUserChannels,
                    'pre-defined'  : self.channels.getPredefinedChannels}[type.lower()]()
                    
        for citem in channels: 
            if self.channels.removeChannel(citem):
                self.removeChannelLineup(citem)
        if self.channels._save():
            return self.saveChannelLineup()
            

    def clearPredefined(self):
        self.log('clearPredefined')
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30077))): return False
            if self.library.clearLibraryItems() and self.clearChannels('pre-defined'):
                setUpdatePending()
                return self.dialog.notificationDialog('%s %s'%(LANGUAGE(30077),LANGUAGE(30053)))


    def clearUserChannels(self):
        self.log('clearUserChannels')
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30093))): return False
            if self.clearChannels('user-defined'):
                setUpdatePending()
                return self.dialog.notificationDialog('%s %s'%(LANGUAGE(30093),LANGUAGE(30053)))


    def clearBlackList(self):
        self.log('clearBlackList') 
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30154))): 
                return False
            return self.library.recommended.clearBlackList()