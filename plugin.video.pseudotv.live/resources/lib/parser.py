#   Copyright (C) 2021 Lunatixz
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
from resources.lib.vault       import Vault
from resources.lib.m3u         import M3U
from resources.lib.xml         import XMLTV
from resources.lib.jsonrpc     import JSONRPC 
from resources.lib.channels    import Channels
from resources.lib.library     import Library
from resources.lib.cache       import Cache
from resources.lib.concurrency import PoolHelper
from resources.lib.rules       import RulesList
from resources.lib.builder     import Builder 
from resources.lib.backup      import Backup

class Writer:
    vault          = Vault()
    globalFileLock = FileLock()
    
    def __init__(self, service=None):
        self.log('__init__')
        if service is None:
            self.monitor   = xbmc.Monitor()
            self.player    = xbmc.Player()
        else:
            self.monitor   = service.monitor
            self.player    = service.player
        
        self.cache         = Cache()
        self.dialog        = Dialog()
        self.pool          = PoolHelper()
        
        self.channels      = Channels(writer=self)
        self.jsonRPC       = JSONRPC(writer=self)
        self.backup        = Backup(writer=self)
        self.builder       = Builder(writer=self)
        self.m3u           = M3U(writer=self)
        self.xmltv         = XMLTV(writer=self)
        self.rules         = RulesList(writer=self)
        
        self.library       = Library(writer=self)
        self.recommended   = self.library.recommended
          
        self.serviceThread = threading.Timer(0.5, self.triggerPendingChange)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def importSETS(self):
        self.log('importSETS')
        importLST = self.channels.getImports()
        
        if SETTINGS.getSettingBool('User_Import'): #append user third-party m3u/xmltv to recommended import list.
            Import_M3U_Path   = {0:SETTINGS.getSetting('Import_M3U_FILE'),
                                 1:SETTINGS.getSetting('Import_M3U_URL')}[SETTINGS.getSettingInt('Import_M3U_TYPE')]
                                 
            Import_XMLTV_Path = {0:SETTINGS.getSetting('Import_XMLTV_FILE'),
                                 1:SETTINGS.getSetting('Import_XMLTV_URL')}[SETTINGS.getSettingInt('Import_XMLTV_TYPE')]

            importLST.append({'item':{'type':'iptv','name':'User M3U/XMLTV',
                                      'm3u':{'path':Import_M3U_Path,'providers':SETTINGS.getSettingList('Import_Provider')},
                                      'xmltv':{'path':Import_XMLTV_Path}}})
        
        for idx, item in enumerate(importLST):
            try:
                importItem = item.get('item',{})
                if importItem.get('type','') != 'iptv': continue
                self.log('importSETS, %s: importItem = %s'%(idx,importItem))
                
                if self.builder.progDialog is not None:
                    self.builder.progDialog = self.dialog.progressBGDialog(self.builder.progress, self.builder.progDialog, message='%s'%(importItem.get('name','')),header='%s, %s'%(ADDON_NAME,LANGUAGE(30151)))
                
                idx += 1
                m3ufle   = importItem.get('m3u'  ,{}).get('path','')
                xmlfle   = importItem.get('xmltv',{}).get('path','')
                
                filters  = {'slug'     :importItem.get('m3u',{}).get('slug',''),
                            'providers':importItem.get('m3u',{}).get('provider',[])}
                            
                self.m3u.importM3U(m3ufle,filters,multiplier=idx)
                self.xmltv.importXMLTV(xmlfle,filters)
            except Exception as e: self.log("importSETS, Failed! %s"%(e), xbmc.LOGERROR)
        return True


    def removeChannel(self, citem, inclLineup=True): #remove channel completely from channels.json and m3u/xmltv
        self.log('removeChannel, inclLineup = %s, citem = %s'%(inclLineup, citem))
        self.channels.removeChannel(citem)
        if inclLineup: self.removeChannelLineup(citem)


    def removeChannelLineup(self, citem): #clean channel from m3u/xmltv
        self.log('removeChannelLineup, citem = %s'%(citem))
        self.m3u.removeStation(citem)
        self.xmltv.removeChannel(citem)
        
                
    def saveChannelLineup(self):
        self.log('saveChannelLineup')
        if self.cleanChannelLineup() and self.importSETS():
            if False in [self.m3u.saveM3U(), 
                         self.xmltv.saveXMLTV()]:
                self.dialog.notificationDialog(LANGUAGE(30001))
                return
        return True
        
        
    def cleanChannelLineup(self):
        # Clean M3U/XMLTV from abandoned channels.
        channels    = self.channels.getChannels()
        m3uChannels = self.m3u.getStations()
        abandoned   = m3uChannels.copy() 
        [abandoned.remove(m3u) for m3u in m3uChannels for channel in channels if channel.get('id') == m3u.get('id')]
        self.log('cleanChannelLineup, abandoned from M3U = %s'%(len(abandoned)))
        for leftover in abandoned: self.removeChannelLineup(leftover)
        return True

        
    def addChannelLineup(self, citem, radio=False, catchup=True):
        item = citem.copy()
        item['label'] = (item.get('label','') or item['name'])
        item['url']   = PVR_URL.format(addon=ADDON_ID,name=urllib.parse.quote(item['name']),id=urllib.parse.quote(item['id']),radio=str(item['radio']))
        if not SETTINGS.getSettingBool('Enable_Grouping'): 
            item['group'] = [ADDON_NAME]
        else:
            item['group'].append(ADDON_NAME)
        item['group'] = list(set(item['group']))
        self.log('addChannelLineup, item = %s, radio = %s, catchup = %s'%(item,radio,catchup))
        self.m3u.addStation(item)
        self.xmltv.addChannel(item)
    

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
            item['categories']  = (file.get('genre','')        or ['Undefined'])
            item['type']        = file.get('type','video')
            item['new']         = int(file.get('playcount','1')) == 0
            item['thumb']       = getThumb(file,SETTINGS.getSettingInt('EPG_Artwork'))
            file['art']['thumb']= getThumb(file,{0:1,1:0}[SETTINGS.getSettingInt('EPG_Artwork')]) #unify thumbnail artwork, opposite of EPG_Artwork
            item['date']        = file.get('premiered','')
            
            if catchup:
                item['catchup-id'] = VOD_URL.format(addon=ADDON_ID,name=urllib.parse.quote(item['title']),id=urllib.parse.quote(encodeString((file.get('originalfile','') or file.get('file','')))),channel=urllib.parse.quote(citem['id']),radio=str(item['radio']))
                file['catchup-id'] = item['catchup-id']
                
            if (item['type'] != 'movie' and ((file.get("season",0) > 0) and (file.get("episode",0) > 0))):
                item['episode-num'] = {'xmltv_ns':'%s.%s'%(file.get("season",1)-1,file.get("episode",1)-1),
                                       'onscreen':'S%sE%s'%(str(file.get("season",0)).zfill(2),str(file.get("episode",0)).zfill(2))}

            item['rating']      = cleanMPAA(file.get('mpaa','') or 'NA')
            item['stars']       = (file.get('rating','')        or '0')
            item['writer']      = ', '.join(file.get('writer',[]))
            item['director']    = ', '.join(file.get('director',[]))
            item['actor']       = ['%s - %s'%(actor.get('name'),actor.get('role','')) for actor in file.get('cast',[]) if actor.get('name')]
            
            file['citem']       = citem #channel item (stale data due to xmltv storage) use for reference.
            item['fitem']       = file  #raw kodi fileitem/listitem, contains citem both passed through 'writer' xmltv param.
            
            streamdetails = file.get('streamdetails',{})
            if streamdetails:
                item['subtitle'] = list(set([sub.get('language','') for sub in streamdetails.get('subtitle',[]) if sub.get('language')]))
                item['language'] = ', '.join(list(set([aud.get('language','') for aud in streamdetails.get('audio',[]) if aud.get('language')])))
                item['audio']    = True if True in list(set([aud.get('codec','') for aud in streamdetails.get('audio',[]) if aud.get('channels',0) >= 2])) else False
                # item.setdefault('video',{})['aspect'] = list(set([vid.get('aspect','')   for vid in streamdetails.get('video',[])    if vid.get('aspect','')]))
            self.xmltv.addProgram(citem['id'], item)
            
            
    def buildPredefinedChannels(self, type=None):
        if not type is None: 
            types = [type]
        else:                
            types = CHAN_TYPES
        self.log('buildPredefinedChannels, types = %s'%(types))
        
        # convert enabled library.json into channels.json items
        def findChannel(citem):
            for idx, eitem in enumerate(echannels):
                if (citem['id'] == eitem['id']) or (citem['type'].lower() == eitem['type'].lower() and citem['name'].lower() == eitem['name'].lower()):
                    return idx, eitem
            return None, {}
                
        def buildAvailableRange():
            # create number array for given type, excluding existing channel numbers.
            start = ((CHANNEL_LIMIT+1)*(CHAN_TYPES.index(type)+1))
            stop  = (start + CHANNEL_LIMIT)
            self.log('buildPredefinedChannels, type = %s, range = %s-%s, enumbers = %s'%(type,start,stop,enumbers))
            return [num for num in range(start,stop) if num not in enumbers]
                           
        # group enabled libraryItems by type
        libraryItems = {} 
        for type in types: 
            libraryItems.setdefault(type,[]).extend(self.library.getLibraryItems(type, enabled=True))
 
        addLST    = []
        leftovers = []
        for type, items in libraryItems.items():
            self.log('buildPredefinedChannels, type = %s'%(type))

            if type == LANGUAGE(30033): #convert enabled imports to channel items.
                self.channels.setImports(items)
            else:
                echannels = list(filter(lambda k:k['type'] == type, self.channels.getPredefinedChannels()))    # existing channels, avoid duplicates, aid in removal.
                enumbers  = [echannel.get('number') for echannel in echannels if echannel.get('number',0) > 0] # existing channel numbers
                numbers   = iter(buildAvailableRange()) #list of available channel numbers 
                leftovers = echannels.copy()

                for item in items:
                    citem = self.channels.getCitem()
                    citem.update({'name'   :getChannelSuffix(item['name'], type),
                                  'path'   :item['path'],
                                  'type'   :item['type'],
                                  'logo'   :item['logo'],
                                  'group'  :[type]})
                    citem['group']   = list(set(citem['group']))
                    citem['radio']   = (item['type'] == LANGUAGE(30097) or 'musicdb://' in item['path'])
                    citem['catchup'] = ('vod' if not citem['radio'] else '')
                    
                    match, eitem = findChannel(citem)
                    if match is not None: #update new citems with existing values.
                        try: leftovers.remove(eitem)
                        except: pass
                            
                        for key in ['id','rules','number','favorite','page']: 
                            citem[key] = eitem[key]
                    else: 
                        citem['number'] = next(numbers,0)
                        citem['id'] = getChannelID(citem['name'],citem['path'],citem['number'])
                    addLST.append(citem)

        # pre-defined citems are all dynamic ie. paths may change. don't update replace with new.
        difference = sorted(diffLSTDICT(leftovers,addLST), key=lambda k: k['number'])
        print('buildPredefinedChannels',difference)
        [self.channels.addChannel(citem) if citem in addLST else self.removeChannel(citem) for citem in difference] #add new, remove old.
        self.log('buildPredefinedChannels, finished building')
        return self.channels.saveChannels()


    def clearChannels(self, type='all'): #clear user-defined channels. all includes pre-defined
        self.log('clearChannels, type = %s'%(type))
        channels = {'all'          : self.channels.getChannels,
                    'user-defined' : self.channels.getUserChannels,
                    'pre-defined'  : self.channels.getPredefinedChannels}[type.lower()]()
        for citem in channels: self.removeChannel(citem)
        if self.channels.saveChannels():
            return self.saveChannelLineup()
            
        
    def recoverChannelsFromBackup(self, file=CHANNELFLE_BACKUP):
        self.log('recoverChannelsFromBackup, file = %s'%(file))
        oldChannels = self.channels.getChannels().copy()
        newChannels = self.channels.loadChannels(CHANNELFLE_BACKUP)
        
        if self.channels.clearChannels():
            difference = sorted(diffLSTDICT(oldChannels,newChannels), key=lambda k: k['number'])
            self.log('recoverChannelsFromBackup, difference = %s'%(len(difference)))
            [self.channels.addChannel(citem) if citem in newChannels else self.channels.removeChannel(citem) for citem in difference] #add new, remove old.
            self.channels.saveChannels()
            
        if self.recoverItemsFromChannels(self.channels.getPredefinedChannels()):
            self.setPendingChangeTimer()
     
       
    def recoverItemsFromChannels(self, predefined=None):
        self.log('recoverItemsFromChannels') #re-enable library.json items from channels.json
        if predefined is None: predefined = self.channels.getPredefinedChannels()
        for type in CHAN_TYPES: 
            items = self.library.getLibraryItems(type)
            if not items: continue #no library items, continue
                
            channels = self.channels.getPredefinedChannelsByType(type, predefined)
            selects  = [idx for idx, item in enumerate(items) for channel in channels if channel.get('name','').lower() == item.get('name','').lower()]
            self.log('recoverItemsFromChannels, type = %s, selects = %s'%(type,selects))
            self.library.setEnableStates(type, selects, items)
        return True
        

    def recoverChannelsFromM3U(self):
        self.log('recoverChannelsFromM3U') #rebuild predefined channels from m3u. #todo reenable predefined. 
        channels = self.channels.getChannels()
        m3u      = self.m3u.getStations().copy()
        if not channels and m3u:
            self.log('recoverChannelsFromM3U, recovering %s m3u channels'%(m3u))
            if not self.dialog.yesnoDialog('%s ?'%(LANGUAGE(30178))): return
            for item in m3u: 
                citem = self.channels.getCitem()
                citem.update(item) #todo repair path.
                self.channels.addChannel(citem)
            return self.channels.saveChannels()
        self.setPendingChangeTimer()
        self.log('recoverChannelsFromM3U, finished')
        return True
        
        
    def autoPagination(self, id, path, limits={}):
        cacheName = '%s.autoPagination.%s.%s'%(ADDON_ID,id,getMD5(path))
        if not limits:
            msg = 'get'
            limits = self.channels.getPage(id) #check channels.json
            if limits.get('total') == 0:       #check cache for fallback
                limits = (self.cache.get(cacheName, checksum=id, json_data=True) or limits)
        else:
            msg = 'set'
            self.cache.set(cacheName, limits, checksum=id, expiration=datetime.timedelta(days=28), json_data=True)
            self.channels.setPage(id, limits)
        self.log("%s autoPagination, id = %s\npath = %s\nlimits = %s"%(msg,id,path,limits))
        return limits
            

    def syncCustom(self): #todo sync user created smartplaylists/nodes for multi-room.
        for type in ['library','playlists']:
            for media in ['video','music','mixed']:
                path  = 'special://userdata/%s/%s/'%(type,media)
                files = FileAccess.listdir(path)[1]
                for file in files:
                    orgpath  = os.path.join(path,file)
                    copypath = os.path.join(PLS_LOC,type,media,file)
                    self.log('copyNodes, orgpath = %s, copypath = %s'%(orgpath,copypath))
                    yield FileAccess.copy(orgpath, copypath)


    def autoTune(self):
        if (isClient() | hasAutotuned()): return False #already ran or dismissed by user, check on next reboot.
        elif self.backup.hasBackup():
            retval = self.dialog.yesnoDialog(LANGUAGE(30132)%(ADDON_NAME,LANGUAGE(30287)), yeslabel=LANGUAGE(30203),customlabel=LANGUAGE(30211))
            if   retval == 2: return self.recoverChannelsFromBackup()
            elif retval != 1:
                setAutoTuned()
                return False
        else:
            if not self.dialog.yesnoDialog(LANGUAGE(30132)%(ADDON_NAME,LANGUAGE(30286))): 
                setAutoTuned()
                return False
       
        busy   = self.dialog.progressBGDialog()
        types  = CHAN_TYPES.copy()
        types.remove(LANGUAGE(30033)) #exclude Imports from auto tuning. ie. Recommended Services
        for idx, type in enumerate(types):
            self.log('autoTune, type = %s'%(type))
            busy = self.dialog.progressBGDialog((idx*100//len(types)), busy, '%s'%(type),header='%s, %s'%(ADDON_NAME,LANGUAGE(30102)))
            self.selectPredefined(type,AUTOTUNE_LIMIT)
        self.dialog.progressBGDialog(100, busy, '%s...'%(LANGUAGE(30053)))
        setAutoTuned()
        return True


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


    def selectPredefined(self, type=None, autoTune=None):
        self.log('selectPredefined, type = %s, autoTune = %s'%(type,autoTune))
        with busy_dialog():
            if isClient(): return
            setSelectOpened(True)
            
            items = self.library.getLibraryItems(type)
            if not items:
                self.dialog.notificationDialog(LANGUAGE(30103)%(type))
                setBusy(False)
                return
                
            listItems = self.pool.poolList(self.library.buildLibraryListitem,items,type)
            if autoTune:
                if autoTune > len(items): autoTune = len(items)
                select = random.sample(list(set(range(0,len(items)))),autoTune)
                
        if not autoTune:
            select = self.dialog.selectDialog(listItems,LANGUAGE(30272)%(type),preselect=list(self.matchLizIDX(listItems,self.library.getEnabledItems(items))))
            
        if not select is None:
            with busy_dialog():
                self.library.setEnableStates(type,list(self.matchDictIDX(items,[listItems[idx] for idx in select])),items)
                self.buildPredefinedChannels(type)
                self.setPendingChangeTimer()
        setSelectOpened(False)
        
        
    def triggerPendingChange(self):
        self.log('triggerPendingChange')
        if isBusy(): self.setPendingChangeTimer()
        else:        setPendingChange()
            
            
    def setPendingChangeTimer(self, wait=30.0):
        self.log('setPendingChangeTimer, wait = %s'%(wait))
        if self.serviceThread.is_alive(): 
            try: self.serviceThread.cancel()
            except: pass
        self.serviceThread = threading.Timer(wait, self.triggerPendingChange)
        self.serviceThread.name = "serviceThread"
        self.serviceThread.start()
        

    def clearPredefined(self):
        self.log('clearPredefined')
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30077))): return False
            if self.library.clearLibraryItems() and self.clearChannels('pre-defined'):
                setAutoTuned(False)
                self.setPendingChangeTimer()
                return self.dialog.notificationDialog(LANGUAGE(30053))


    def clearUserChannels(self):
        self.log('clearUserChannels')
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30093))): return False
            if self.clearChannels('user-defined'):
                setAutoTuned(False)
                self.setPendingChangeTimer()
                return self.dialog.notificationDialog(LANGUAGE(30053))


    def clearBlackList(self):
        self.log('clearBlackList') 
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30154))): 
                return False
            return self.library.recommended.clearBlackList()