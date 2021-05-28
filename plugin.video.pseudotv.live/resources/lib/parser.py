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
from resources.lib.m3u         import M3U
from resources.lib.xml         import XMLTV
from resources.lib.vault       import Vault
from resources.lib.channels    import Channels
from resources.lib.library     import Library

class Writer:
    GlobalFileLock = FileLock()
    
    def __init__(self, inherited=None):
        self.log('__init__')
        if inherited:
            self.monitor      = inherited.monitor
            self.player       = inherited.player
            self.cache        = inherited.cache
            self.dialog       = inherited.dialog
            self.pool         = inherited.pool
            self.rules        = inherited.rules
        else:
            from resources.lib.cache       import Cache
            from resources.lib.concurrency import PoolHelper
            from resources.lib.rules       import RulesList
            self.monitor      = xbmc.Monitor()
            self.player       = xbmc.Player()
            self.cache        = Cache()
            self.dialog       = Dialog()
            self.pool         = PoolHelper()
            self.rules        = RulesList()
        
        if inherited.__class__.__name__ in ['Builder','Config']:
            self.progDialog   = inherited.progDialog
            self.progress     = inherited.progress
            self.chanName     = inherited.chanName
        else:
            self.progDialog   = None
            self.progress     = None
            self.chanName     = None
            
        if not inherited.__class__.__name__ == 'JSONRPC':
            from resources.lib.jsonrpc import JSONRPC 
            self.jsonRPC      = JSONRPC(self)
        else:
            self.jsonRPC      = inherited
        
        self.vault            = Vault()   
        self.channels         = Channels(writer=self)
        self.library          = Library(writer=self)
        self.recommended      = self.library.recommended
        
        self.m3u              = M3U(writer=self)
        self.xmltv            = XMLTV(writer=self)
      
      
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
        
    def getChannelEndtimes(self):
        self.log('getChannelEndtimes')
        now        = datetime.datetime.fromtimestamp(getLocalTime())
        channels   = self.xmltv.getChannels()
        programmes = self.xmltv.getProgrammes()
        for channel in channels:
            try: 
                stopDate = max([strpTime(program['stop'], DTFORMAT).timetuple() for program in programmes if program['channel'] == channel['id']], default=now)
                yield channel['id'],time.mktime(stopDate)
            except ValueError: pass
            except Exception as e:
                self.log("getChannelEndtimes, Failed!\n%s\nremoving malformed xmltv channel/programmes %s"%(e,channel.get('id')), xbmc.LOGERROR)
                self.removeChannelLineup(channel) #something went wrong; remove channel from m3u/xmltv force fresh rebuild.
         
         
    def importSETS(self):
        self.log('importSETS')
        importLST = self.channels.getImports()
        
        if SETTINGS.getSettingBool('User_Import'): #append user third-party m3u/xmltv to recommended import list.
            Import_M3U_Path   = {0:SETTINGS.getSetting('Import_M3U_FILE')  ,
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
                
                if self.progDialog is not None:
                    self.progDialog = self.dialog.progressBGDialog(self.progress, self.progDialog, message='%s'%(importItem.get('name','')),header='%s, %s'%(ADDON_NAME,LANGUAGE(30151)))
                
                idx += 1
                m3ufle   = importItem.get('m3u'  ,{}).get('path','')
                xmlfle   = importItem.get('xmltv',{}).get('path','')
                
                filters  = {'slug'     :importItem.get('m3u',{}).get('slug',''),
                            'providers':importItem.get('m3u',{}).get('provider',[])}
                            
                self.m3u.importM3U(m3ufle,filters,multiplier=idx)
                self.xmltv.importXMLTV(xmlfle,filters)
            except Exception as e: self.log("importSETS, Failed! %s"%(e), xbmc.LOGERROR)
        return True
        
        
    def saveChannels(self):
        self.log('saveChannels')
        SETTINGS.setSetting('Select_Channels','[B]%s[/B] Channels'%(len(self.channels.getChannels())))
        return self.channels.save()
        
        
    def saveChannelLineup(self):
        self.log('saveChannelLineup')
        if self.cleanChannelLineup() and self.importSETS():
            if False in [func.save() for func in [self.m3u, self.xmltv]]:
                self.dialog.notificationDialog(LANGUAGE(30001))
                return
        return True
        
    
    def removeChannel(self, citem, inclLineup=True): #remove channel completely from channels.json and m3u/xmltv
        self.log('removeChannel, citem = %s'%(citem))
        self.channels.removeChannel(citem)
        if inclLineup: self.removeChannelLineup(citem)
        
                
    def removeChannelLineup(self, citem): #clean channel from m3u/xmltv
        self.log('removeChannelLineup, citem = %s'%(citem))
        self.m3u.removeChannel(citem)
        self.xmltv.removeChannel(citem)
        
    
    def addChannelLineup(self, citem, radio=False, catchup=True):
        item = citem.copy()
        item['label'] = (item.get('label','') or item['name'])
        item['url']   = 'plugin://%s/?mode=play&name=%s&id=%s&radio=%s'%(ADDON_ID,urllib.parse.quote(item['name']),urllib.parse.quote(item['id']),str(item['radio']))
        if not SETTINGS.getSettingBool('Enable_Grouping'): 
            item['group'] = [ADDON_NAME]
        else:
            item['group'].append(ADDON_NAME)
        item['group'] = list(set(item['group']))
        self.log('addChannelLineup, item = %s, radio = %s, catchup = %s'%(item,radio,catchup))
        self.m3u.addChannel(item)
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
            item['rating']      = cleanMPAA(file.get('mpaa','')or 'NA')
            item['stars']       = (file.get('rating','')       or '0')
            item['categories']  = (file.get('genre','')        or ['Undefined'])
            item['type']        = file.get('type','video')
            item['new']         = int(file.get('playcount','1')) == 0
            item['thumb']       = getThumb(file,SETTINGS.getSettingInt('EPG_Artwork'))
            file['art']['thumb']= getThumb(file,{0:1,1:0}[SETTINGS.getSettingInt('EPG_Artwork')]) #unify thumbnail artwork, opposite of EPG_Artwork
            item['date']        = file.get('premiered','')
            
            if catchup:
                item['catchup-id'] = 'plugin://%s/?mode=vod&name=%s&id=%s&channel=%s&radio=%s'%(ADDON_ID,urllib.parse.quote(item['title']),urllib.parse.quote(encodeString((file.get('originalfile','') or file.get('file','')))),urllib.parse.quote(citem['id']),str(item['radio']))
            
            if (item['type'] != 'movie' and ((file.get("season",0) > 0) and (file.get("episode",0) > 0))):
                item['episode-num'] = {'xmltv_ns':'%s.%s'%(file.get("season",1)-1,file.get("episode",1)-1),
                                       'onscreen':'S%sE%s'%(str(file.get("season",0)).zfill(2),str(file.get("episode",0)).zfill(2))}

            item['director']    = (','.join(file.get('director',[])))
            item['writer']      = (','.join(file.get('writer',[])))
            
            file['citem']       = citem #channel dict (stale data due to xmltv storage)
            item['fitem']       = file # kodi fileitem/listitem dict.
            
            # streamdetails        = file.get('streamdetails',{})
            # if streamdetails:
                # item['subtitle'] = list(set([sub.get('language','') for sub in streamdetails.get('subtitle',[]) if sub.get('language','')]))
                # item['audio']    = list(set([aud.get('codec','')    for aud in streamdetails.get('audio',[])    if aud.get('codec','')]))
                # item['language'] = list(set([aud.get('language','') for aud in streamdetails.get('audio',[])    if aud.get('language','')]))
                # item['video']    = list(set([vid.get('aspect','')   for vid in streamdetails.get('video',[])    if vid.get('aspect','')]))
            
            self.xmltv.addProgram(citem['id'], item)
            
            
    def cleanChannelLineup(self):
        # Clean M3U of Channels with no guidedata.
        m3uChannels = self.m3u.getChannels()
        xmlChannels = self.xmltv.getChannels()
        abandoned   = m3uChannels.copy() 
        [abandoned.remove(m3u) for xmltv in xmlChannels for m3u in m3uChannels if xmltv.get('id') == m3u.get('id')]
        self.log('cleanChannelLineup, abandoned from M3U = %s'%(len(abandoned)))
        for leftover in abandoned: self.removeChannelLineup(leftover)
                
        # Clean XMLTV of Abandoned Channels.
        channels    = self.channels.getChannels()
        xmlChannels = self.xmltv.getChannels()
        abandoned   = xmlChannels.copy() 
        [abandoned.remove(xmltv) for xmltv in xmlChannels for channel in channels if xmltv.get('id') == channel.get('id')]
        self.log('cleanChannelLineup, abandoned from M3U = %s'%(len(abandoned)))
        for leftover in abandoned: self.removeChannelLineup(leftover)
        return True


    def clearChannels(self, all=False): #clear user-defined channels. all includes pre-defined
        self.log('clearChannels, all = %s'%(all))
        if all: self.channels.clear()
        else:
            channels = list(filter(lambda citem:citem.get('number') <= CHANNEL_LIMIT, self.channels.getChannels()))
            for citem in channels: self.removeChannel(citem)
        if self.saveChannels():
            return self.saveChannelLineup()
            
        
    def recoverChannelsFromBackup(self, file=CHANNELFLE_BACKUP):
        self.log('recoverChannelsFromBackup, file = %s'%(file))
        oldChannels = self.channels.getChannels().copy()
        newChannels = self.channels.cleanSelf(self.channels.load(CHANNELFLE_BACKUP)).get('channels',[])
        if self.channels.clear():
            difference = sorted(diffLSTDICT(oldChannels,newChannels), key=lambda k: k['number'])
            self.log('recoverChannelsFromBackup, difference = %s'%(len(difference)))
            [self.channels.addChannel(citem) if citem in newChannels else self.channels.removeChannel(citem) for citem in difference] #add new, remove old.
            self.channels.save()
        setRestartRequired()
        self.log('recoverChannelsFromBackup, finished')
        return True
        
        
    def recoverChannelsFromM3U(self):
        self.log('recoverChannelsFromM3U') #rebuild channels.json from m3u. #todo reenable predefined. 
        # channels = self.channels.getChannels()
        # m3u      = self.m3u.getChannels().copy()
        # if not channels and m3u:
            # self.log('recoverChannelsFromM3U, recovering %s m3u channels'%(m3u))
            # if not self.dialog.yesnoDialog('%s ?'%(LANGUAGE(30178))): return
            # for item in m3u: 
                # citem = self.channels.getCitem()
                # citem.update(item) #todo repair path.
                # self.channels.addChannel(citem)
            # return self.saveChannels()
        # setRestartRequired()
        # self.log('recoverChannelsFromM3U, finished')
        return True
     
       
    def recoverItemsFromChannels(self):
        self.log('recoverItemsFromChannels')
        #todo chk 4 empty library.json and full channels.json then recover.
        # ##re-enable library.json items from channels.json
        # for type in CHAN_TYPES: 
            # if self.monitor.waitForAbort(0.01): break
            # items = self.library.getLibraryItems(type)
            # if not items: continue
            # channels = self.channels.getPredefinedChannelsByType(type)
            # if not channels: continue
                
            # selects = []
            # for idx, item in enumerate(items):
                # for channel in channels:
                    # if channel.get('name','').lower() == item.get('name','').lower():
                        # selects.append(idx)
                        
            # self.log('recoverItemsFromChannels, type = %s, selects = %s'%(type,selects))
            # if selects: self.library.setEnableStates(type, selects, items)
        # setPendingChange()
        # self.log('recoverItemsFromChannels, finished')
        return True
        

    def convertLibraryItems(self, type=None):
        if not type is None: types = [type]
        else:                types = CHAN_TYPES
        self.log('convertLibraryItems, types = %s'%(types))
        # group enabled libraryItems by type
        items = {} 
        for type in types: items.setdefault(type,[]).extend(self.library.getLibraryItems(type, enabled=True))
        return self.buildPredefinedChannels(items) 


    def buildPredefinedChannels(self, libraryItems):
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
            self.log('buildAvailableRange, type = %s, range = %s-%s, enumbers = %s'%(type,start,stop,enumbers))
            return [num for num in range(start,stop) if num not in enumbers]
                
        addLST    = []
        removeLST = []
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
                        if eitem in removeLST: leftovers.remove(eitem)
                        for key in ['id','rules','number','favorite','page']: 
                            citem[key] = eitem[key]
                    else: 
                        citem['number'] = next(numbers,0)
                        citem['id'] = getChannelID(citem['name'],citem['path'],citem['number'])
                    addLST.append(citem)
                removeLST.extend(leftovers)
            
        # pre-defined citems are all dynamic ie. paths may change. don't update replace with new.
        difference = sorted(diffLSTDICT(removeLST,addLST), key=lambda k: k['number'])
        [self.channels.addChannel(citem) if citem in addLST else self.removeChannel(citem) for citem in difference] #add new, remove old.
        self.log('buildPredefinedChannels, finished building')
        return self.saveChannels()
        
        
    def autoPagination(self, id, path, limits={}):
        cacheName = '%s.autoPagination.%s.%s'%(ADDON_ID,id,path)
        if not limits:
            msg = 'get'
            limits = self.channels.getPage(id) #check channels.json
            if limits.get('total') == 0:       #check cache for fallback
                limits = (self.cache.get(cacheName, checksum=id, json_data=True) or limits)
        else:
            msg = 'set'
            self.cache.set(cacheName, limits, checksum=id, expiration=datetime.timedelta(days=28), json_data=True)
            if self.channels.setPage(id, limits): self.channels.save()
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
