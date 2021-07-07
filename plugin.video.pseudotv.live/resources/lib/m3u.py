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
# https://github.com/kodi-pvr/pvr.iptvsimple/blob/Matrix/README.md#m3u-format-elements
# -*- coding: utf-8 -*-
     
from resources.lib.globals     import *

class M3U:
    def __init__(self, writer=None):
        self.log('__init__')
        if writer is None:
            from resources.lib.parser import Writer
            writer = Writer()
        self.writer = writer
            
        if self.writer.vault.m3uList is None:
            self._reload()
        else:
            self._withdraw()
            

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def _clear(self):
        self.log('_clear')
        self.writer.vault.m3uList  = {}
        return self._deposit()
        
        
    def _reload(self):
        self.log('reload')
        self.writer.vault.m3uList = self._load()
        return self._deposit()
        
     
    def _deposit(self):
        self.log('_deposit')
        self.writer.vault.set_m3uList(self.writer.vault.m3uList)
        return True
        
    
    def _withdraw(self):
        self.log('_withdraw')
        self.writer.vault.m3uList = self.writer.vault.get_m3uList()
        return True
        

    def _load(self):
        self.log('_load')
        return {'data':'#EXTM3U tvg-shift="" x-tvg-url="" x-tvg-id="" catchup-correction=""',
                'channels':self.cleanSelf(self.loadM3U())}
        

    def loadM3U(self, file=getUserFilePath(M3UFLE)):
        self.log('loadM3U, file = %s'%file)
        if file.startswith('http'):
            url  = file
            file = os.path.join(TEMP_LOC,slugify(url),'.m3u')
            saveURL(url,file)
            
        with fileLocker(self.writer.globalFileLock):
            fle   = FileAccess.open(file, 'r')
            lines = (fle.readlines())
            data  = lines.pop(0)
            fle.close()
            
        chCount = 0
        data    = {}
        for idx, line in enumerate(lines):
            line = line.rstrip()
            if line.startswith('#EXTM3U'):
                data = {'tvg-shift'         :re.compile('tvg-shift=\"(.*?)\"'          , re.IGNORECASE).search(line),
                        'x-tvg-url'         :re.compile('x-tvg-url=\"(.*?)\"'          , re.IGNORECASE).search(line),
                        'catchup-correction':re.compile('catchup-correction=\"(.*?)\"' , re.IGNORECASE).search(line)}

            elif line.startswith('#EXTINF:'):
                chCount += 1
                match = {'number'            :re.compile('tvg-chno=\"(.*?)\"'           , re.IGNORECASE).search(line),
                         'id'                :re.compile('tvg-id=\"(.*?)\"'             , re.IGNORECASE).search(line),
                         'name'              :re.compile('tvg-name=\"(.*?)\"'           , re.IGNORECASE).search(line),
                         'logo'              :re.compile('tvg-logo=\"(.*?)\"'           , re.IGNORECASE).search(line),
                         'group'             :re.compile('group-title=\"(.*?)\"'        , re.IGNORECASE).search(line),
                         'radio'             :re.compile('radio=\"(.*?)\"'              , re.IGNORECASE).search(line),
                         'label'             :re.compile(',(.*)'                        , re.IGNORECASE).search(line),
                         'tvg-shift'         :re.compile('tvg-shift=\"(.*?)\"'          , re.IGNORECASE).search(line),
                         'x-tvg-url'         :re.compile('x-tvg-url=\"(.*?)\"'          , re.IGNORECASE).search(line),
                         'catchup'           :re.compile('catchup=\"(.*?)\"'            , re.IGNORECASE).search(line),
                         'catchup-source'    :re.compile('catchup-source=\"(.*?)\"'     , re.IGNORECASE).search(line),
                         'catchup-days'      :re.compile('catchup-days=\"(.*?)\"'       , re.IGNORECASE).search(line),
                         'catchup-correction':re.compile('catchup-correction=\"(.*?)\"' , re.IGNORECASE).search(line),
                         'provider'          :re.compile('provider=\"(.*?)\"'           , re.IGNORECASE).search(line),
                         'provider-type'     :re.compile('provider-type=\"(.*?)\"'      , re.IGNORECASE).search(line),
                         'provider-logo'     :re.compile('provider-logo=\"(.*?)\"'      , re.IGNORECASE).search(line),
                         'provider-languages':re.compile('provider-languages=\"(.*?)\"' , re.IGNORECASE).search(line)}
                
                item = self.writer.channels.getCitem()
                item.update({'number' :chCount,
                             'logo'   :LOGO,
                             'catchup':''})
                
                for key in match.keys():
                    if not match[key]:
                        if data.get(key):
                            self.log('loadM3U, using #EXTM3U "%s" value for #EXTINF')%(key)
                            match[key] = data[key] #no local EXTINF value found; use EXTM3U if applicable.
                        else: continue
                    item[key] = match[key].group(1)
                    if key == 'logo':
                        item[key] = self.writer.jsonRPC.resources.cleanLogoPath(item[key])
                    elif key == 'number':
                        try:    item[key] = int(item[key])
                        except: item[key] = float(item[key])
                    elif key == 'group':
                        item[key] = list(filter(None,list(set(item[key].split(';')))))
                        if ADDON_NAME in item[key]: item[key].remove(ADDON_NAME)
                    elif key == 'radio':
                        item[key] = item[key].lower() == 'true'

                for nidx in range(idx+1,len(lines)):
                    try:
                        nline = lines[nidx].rstrip()
                        if   nline.startswith('#EXTINF:'): break
                        # elif nline.startswith('#EXTVLCOPT'):
                        # elif nline.startswith('#EXT-X-PLAYLIST-TYPE'):
                        elif nline.startswith('#EXTGRP'):
                            group = re.compile('^#EXTGRP:(.*)$', re.IGNORECASE).search(nline)
                            if group: 
                                item['group'].append(prop.group(1).split(';'))
                                item['group'] = list(set(item['group']))
                        elif nline.startswith('#KODIPROP:'):
                            prop = re.compile('^#KODIPROP:(.*)$', re.IGNORECASE).search(nline)
                            if prop: item.setdefault('kodiprops',[]).append(prop.group(1))
                        elif nline.startswith('##'): continue
                        elif not nline: continue
                        else: item['url'] = nline
                    except Exception as e: self.log('loadM3U, error parsing m3u! %s'%(e))
                        
                item['name']  = (item.get('name','')  or item.get('label',''))
                item['label'] = (item.get('label','') or item.get('name',''))
                if not item.get('id','') or not item.get('name','') or not item.get('number',''): 
                    self.log('loadM3U, SKIPPED MISSING META item = %s'%item)
                    continue
                self.log('loadM3U, item = %s'%item)
                yield item
                    

    def saveM3U(self):
        self.log('saveM3U')
        with fileLocker(self.writer.globalFileLock):
            filePath = getUserFilePath(M3UFLE)
            fle = FileAccess.open(filePath, 'w')
            self.log('saveM3U, saving to %s'%(filePath))
            fle.write('%s\n'%(self.writer.vault.m3uList['data']))
            keys     = list(self.writer.channels.getCitem().keys())
            keys.extend(['kodiprops','label'])#add keys to ignore from optional.
            citem    = '#EXTINF:-1 tvg-chno="%s" tvg-id="%s" tvg-name="%s" tvg-logo="%s" group-title="%s" radio="%s" catchup="%s" %s,%s\n'
            channels = self.sortStations(self.writer.vault.m3uList.get('channels',[]))
            
            for channel in channels:
                optional = ''
                if not channel: continue
                    
                # write optional m3u parameters.
                for key, value in channel.items():
                    if key in keys: continue
                    elif value: optional += '%s="%s" '%(key,value)
                        
                fle.write(citem%(channel['number'],
                                 channel['id'],
                                 channel['name'],
                                 channel['logo'],
                                 ';'.join(channel['group']),
                                 channel['radio'],
                                 channel['catchup'],
                                 optional,
                                 channel['label']))
                                 
                if channel.get('kodiprops',[]):
                    fle.write('%s\n'%('\n'.join(['#KODIPROP:%s'%(prop) for prop in channel['kodiprops']])))
                fle.write('%s\n'%(channel['url']))
            fle.close()
            return self._reload()
        
        
    def deleteM3U(self):
        self.log('deleteM3U')
        if FileAccess.delete(getUserFilePath(M3UFLE)): return self.writer.dialog.notificationDialog(LANGUAGE(30016)%('M3U'))
        return False
        
        
    @staticmethod
    def cleanSelf(channels, key='id', slug='@%s'%(slugify(ADDON_NAME))):
        log('M3U: cleanSelf, slug = %s'%(slug)) # remove imports (Non PseudoTV Live)
        if not slug: return channels
        return list(filter(lambda line:line.get(key,'').endswith(slug), channels))
        
        
    @staticmethod
    def sortStations(channels):
        return sorted(channels, key=lambda k: k['number'])
        
        
    def importM3U(self, file, filters={}, multiplier=1):
        self.log('importM3U, file = %s, filters = %s, multiplier = %s'%(file,filters,multiplier))
        try:
            if file.startswith('http'):
                url  = file
                file = os.path.join(TEMP_LOC,'%s.m3u'%(slugify(url)))
                saveURL(url,file)
                
            importChannels = []
            channels = self.loadM3U(file)
            
            for key, value in filters.items():
                if key == 'slug' and value:
                    importChannels.extend(self.cleanSelf(channels,'id',value))
                elif key == 'providers' and value:
                    for provider in value: 
                        importChannels.extend(self.cleanSelf(channels,'provider',provider))
            
            #no filter found, import all channels.
            if not importChannels: 
                importChannels.extend(channels)
                
            importChannels = list(self.chkImport(importChannels,multiplier))
            self.log('importM3U, found import stations = %s'%(len(importChannels)))
            self.writer.vault.m3uList.get('channels',[]).extend(self.sortStations(importChannels))
                
        except Exception as e: self.log("importM3U, failed! " + str(e), xbmc.LOGERROR)
        return True
        
        
    def chkImport(self, channels, multiplier=1):
        def roundup(x):
            return x if x % 1000 == 0 else x + 1000 - x % 1000
            
        def frange(start, stop, step):
          while not self.writer.monitor.abortRequested() and start < stop:
            yield float(start)
            start += decimal.Decimal(step)

        channels  = self.sortStations(channels)
        chstart   = roundup((CHANNEL_LIMIT * len(CHAN_TYPES)+1))
        chmin     = int(chstart + (multiplier*1000))
        chmax     = int(chmin + (CHANNEL_LIMIT))
        chrange   = list(frange(chmin,chmax,0.1))
        leftovers = []
        self.log('chkImport, channels = %s, multiplier = %s, chstart = %s, chmin = %s, chmax = %s'%(len(channels),multiplier,chstart,chmin,chmax))
        ## check tvg-chno for conflict, use multiplier to modify org chnum.
        for citem in channels:
            if len(chrange) == 0:
                self.log('chkImport, reached max import')
                break
            elif citem['number'] < CHANNEL_LIMIT: 
                newnumber = (chmin+citem['number'])
                if newnumber in chrange:
                    chrange.remove(newnumber)
                    citem['number'] = newnumber
                    yield citem
                else: leftovers.append(citem)
            else: leftovers.append(citem)
        
        for citem in leftovers:
            if len(chrange) == 0:
                self.log('chkImport, reached max import')
                break
            else:
                citem['number'] = chrange.pop(0)
                yield citem
            
            
    def getShift(self):
        self.log('getShift') 
        return ((time.mktime(time.localtime()) - time.mktime(time.gmtime())) / 60 / 60)

    
    def getStations(self):
        self.log('getStations')
        return self.sortStations(self.writer.vault.m3uList.get('channels',[]))
        
        
    def addStation(self, item):
        self.log('addStation, item = %s'%(item))
        item['provider']      = ADDON_NAME
        item['provider-type'] = 'local'
        item['provider-logo'] = HOST_LOGO
        idx, line = self.findStation(item)
        if idx is None: self.writer.vault.m3uList.get('channels',[]).append(item)
        else: self.writer.vault.m3uList.get('channels',[])[idx] = item # replace existing channel
        return True


    def findStation(self, citem, channels=None):
        if channels is None: channels = self.writer.vault.m3uList.get('channels',[])
        for idx, line in enumerate(channels):
            if line.get('id') == citem.get('id'):
                self.log('findStation, idx = %s, line = %s'%(idx, line))
                return idx, line
        return None, {}
        
        
    def removeStation(self, citem):
        self.log('removeStation id = %s'%(citem['id']))
        idx, line = self.findStation(citem)
        if idx is not None: self.writer.vault.m3uList['channels'].pop(idx)
        return True