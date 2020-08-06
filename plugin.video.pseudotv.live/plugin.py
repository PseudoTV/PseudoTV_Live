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
from resources.lib.builder import Builder

class Plugin:
    def __init__(self, sysARG=sys.argv):
        log('__init__, sysARG = ' + str(sysARG))
        self.sysARG = sysARG
        self.CONTENT_TYPE  = 'episodes'
        self.CACHE_ENABLED = False
        self.myBuilder = Builder()
        self.myBuilder.plugin = self
        self.myPlayer = MY_PLAYER
        self.playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.maxDays  = getSettingInt('Max_Days')
        self.seekTol  = getSettingInt('Seek_Tolerance')
        self.usePlaylist = bool(getSettingInt('Playback_Method'))
        
        
    def buildMenu(self, name=None):
        log('buildMenu, name = %s'%name)
        MAIN_MENU = [(LANGUAGE(30008), '', '')]#,#todo
                     # (LANGUAGE(30009), '', '')]

        UTIL_MENU = [#(LANGUAGE(30010), '', '', LANGUAGE(30008)),
                     (LANGUAGE(30011), '', '', LANGUAGE(30008)),
                     (LANGUAGE(30096), '', '', LANGUAGE(30096)),
                     (LANGUAGE(30012)%(getPluginMeta(PVR_CLIENT).get('name',''),ADDON_NAME,), '', '', LANGUAGE(30008)),
                     (LANGUAGE(30065)%(getPluginMeta(PVR_CLIENT).get('name','')), '', '', LANGUAGE(30008)),
                     (LANGUAGE(30081), '', '', LANGUAGE(30008)),
                     (LANGUAGE(30013), '', '', LANGUAGE(30008))]

        CHAN_MENU = [(LANGUAGE(30014), '', '', LANGUAGE(30009)),
                     (LANGUAGE(30015), '', '', LANGUAGE(30009))]

        if   name is None:            items = MAIN_MENU
        elif name == LANGUAGE(30008): items = UTIL_MENU
        elif name == LANGUAGE(30009): items = CHAN_MENU
        else: return
        [self.addDir(*item) for item in items]
        
        
    def deleteFiles(self, channels=True):
        log('utilities, deleteFiles')
        msg = 30096 if channels else 30011
        if yesnoDialog('%s ?'%(LANGUAGE(msg))):
            if channels: 
                self.myBuilder.channels.delete()
            else:
                [func() for func in [self.myBuilder.m3u.delete,self.myBuilder.xmltv.delete]]
        return
        
        
    def utilities(self, name):
        log('utilities, name = %s'%name)
        if name   == LANGUAGE(30010): self.myBuilder.buildService()
        elif name == LANGUAGE(30011): self.deleteFiles()
        elif name == LANGUAGE(30096): self.deleteFiles(channels=True)
        elif name == LANGUAGE(30012)%(getPluginMeta(PVR_CLIENT).get('name',''),ADDON_NAME,): configurePVR()
        elif name == LANGUAGE(30065)%(getPluginMeta(PVR_CLIENT).get('name','')): brutePVR()
        elif name == LANGUAGE(30013): REAL_SETTINGS.openSettings()
        elif name == LANGUAGE(30081): textviewer(getProperty('USER_LOG'),usemono=True)
        else: return
        xbmc.executebuiltin('Action(Back,10025)')
            
            
    def channels(self, name):
        log('channels, name = %s'%name)
        if name   == LANGUAGE(30014): self.buildChannels() 
        elif name == LANGUAGE(30015): return #todo prompt user, self.myBuilder.playlist.clearChannelList()
        else: return
        xbmc.executebuiltin('Action(back)')
           

    def buildChannels(self):
        log('buildChannels')
        channelList = self.myBuilder.createChannelItems()
        items = [(item['name'], item['number'], item['path'], '', item['logo']) for item in channelList]
        for item in items: self.addDir(*item)


    def contextPlay(self, writer, isPlaylist=False):
        stpos  = 0
        writer = loadJSON(writer.replace(' /  "',' , "').replace(" /  ",", "))# current item
        if not writer: 
            return notificationDialog(LANGUAGE(30001))
            
        log('contextPlay, writer = %s, isPlaylist = %s'%(dumpJSON(writer),isPlaylist))
        self.playlist.clear()
        xbmc.sleep(100)
        if not isPlaylist:
            liz = buildItemListItem(writer)
            listitems = [liz]
        else:
            channelData = writer.get('data',{}) 
            if not channelData: 
                return notificationDialog(LANGUAGE(30001))
            
            pvritem     = self.myBuilder.jsonRPC.getPVRposition(channelData.get('name',''), channelData.get('id',''), isPlaylist=isPlaylist)
            nowitem     = pvritem.get('broadcastnow',{})
            nextitems   = pvritem.get('broadcastnext',[])[slice(0, PAGE_LIMIT)] # list of upcoming items, truncate for speed.
            nextitems.insert(0,nowitem)
            
            for pos, nextitem in enumerate(nextitems):
                if loadJSON(nextitem.get('writer',{})).get('file','') == writer.get('file',''):
                    stpos = pos
                    break
            log('contextPlay, writer stpos = %s'%(stpos))
            listitems = ([buildItemListItem(loadJSON(nextitem.get('writer',''))) for nextitem in nextitems]) 
            
        [self.playlist.add(lz.getPath(),lz,idx) for idx,lz in enumerate(listitems)]
        if isPlaylistRandom(): self.playlist.unshuffle()
        return self.myPlayer.play(self.playlist, startpos=stpos)

        
    def playRadio(self, name, id):
        log('playRadio, id = %s'%(id))
        pvritem = self.myBuilder.jsonRPC.getPVRposition(name, id, radio=True)
        nowitem = pvritem.get('broadcastnow',{}) # current item
        writer  = loadJSON(nowitem.get('writer',{}))
        if not writer: 
            notificationDialog(LANGUAGE(30001))
            return xbmcplugin.setResolvedUrl(int(self.sysARG[1]), False, xbmcgui.ListItem())
            
        json_response = self.myBuilder.jsonRPC.requestList(id, writer.get('data',{}).get('path',''), 'music', page=250)
        if json_response:
            setCurrentChannelItem(pvritem)
            self.playlist.clear()
            xbmc.sleep(100)
            listitems = [buildItemListItem(item, mType='music') for item in json_response]
            [self.playlist.add(lz.getPath(),lz,idx) for idx,lz in enumerate(listitems)]
            if isPlaylistRandom(): self.playlist.unshuffle()
            log('playRadio, Playlist size = %s'%(self.playlist.size()))
            return self.myPlayer.play(self.playlist)
        
        
    def playChannel(self, name, id, isPlaylist=False, failed=False):
        log('playChannel, id = %s, isPlaylist = %s'%(id,isPlaylist))
        found = False
        liz       = xbmcgui.ListItem()
        listitems = [liz] #empty listitem required to pass failed playback.
        pvritem   = self.myBuilder.jsonRPC.getPVRposition(name, id, isPlaylist=isPlaylist)
        nowitem   = pvritem.get('broadcastnow',{}) # current item
        nextitems = pvritem.get('broadcastnext',[])[slice(0, PAGE_LIMIT)] # list of upcoming items, truncate for speed.
        ruleslist = []#check pre-play channel rules.
        
        if nowitem:
            found = True
            setCurrentChannelItem(pvritem)
            progress = nowitem['progress']
            runtime  = nowitem['runtime']
            writer   = loadJSON(nowitem.get('writer',{}))
            liz = buildItemListItem(writer)
            if (progress > self.seekTol):
                # near end, avoid loopback; override last listitem and queue next show.
                if (progress > ((runtime * 60) - 45)): #45sec endtime offset
                    log('playChannel, progress = %s near end, queue nextitem'%(progress))
                    liz = buildItemListItem(loadJSON(nextitems[0].get('writer',{})))
                else:
                    log('playChannel, progress = %s within seek tolerance setting seek.'%(progress))
                    liz.setProperty('totaltime'  , str((runtime * 60)))
                    liz.setProperty('resumetime' , str(progress))
                    liz.setProperty('startoffset', str(progress))
                    
                    # remove bct pre-roll from stack://
                    url  = liz.getPath()
                    file = writer.get('originalfile','')
                    if url.startswith('stack://') and not url.startswith('stack://%s'%(file)):
                        log('playChannel, playing stack with url = %s'%(url))
                        paths = url.split(' , ')
                        for path in paths:
                            if file not in path: 
                                paths.remove(path)
                            elif file in path: 
                                break
                        liz.setPath('stack://%s'%(' , '.join(paths)))
                
            listitems = [liz]
            if isPlaylist: 
                self.playlist.clear()
                xbmc.sleep(100)
                listitems.extend([buildItemListItem(loadJSON(nextitem.get('writer',''))) for nextitem in nextitems])            
                [self.playlist.add(lz.getPath(),lz,idx) for idx,lz in enumerate(listitems)]
                if isPlaylistRandom(): self.playlist.unshuffle()
                log('playChannel, Playlist size = %s'%(self.playlist.size()))
                return self.myPlayer.play(self.playlist)
            # else:
                # listitems.extend([buildItemListItem(loadJSON(nextitem.get('writer',''))) for nextitem in nextitems])  
                # paths = [lz.getPath() for lz in listitems]
                # liz.setPath('stack://%s'%(' , '.join(paths)))
                # listitems = [liz]
            #todo found == False set fallback to nextitem? with playlist and failed == True?
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitems[0])


    def addLink(self, name, channel, path, mode='',icon=ICON, liz=None, total=0):
        if liz is None:
            liz=xbmcgui.ListItem(name)
            liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
            liz.setArt({'thumb':icon,'logo':icon,'icon':icon})
        log('addLink, name = %s'%(name))
        u=self.sysARG[0]+"?url="+urllib.parse.quote(path)+"&channel="+str(channel)+"&name="+urllib.parse.quote(name)+"&mode="+str(mode)
        xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,totalItems=total)


    def addDir(self, name, channel, path, mode='',icon=ICON, liz=None):
        log('addDir, name = %s'%(name))
        if liz is None:
            liz=xbmcgui.ListItem(name)
            liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
            liz.setArt({'thumb':icon,'logo':icon,'icon':icon})
        liz.setProperty('IsPlayable', 'false')
        u=self.sysARG[0]+"?url="+urllib.parse.quote(path)+"&channel="+str(channel)+"&name="+urllib.parse.quote(name)+"&mode="+str(mode)
        xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,isFolder=True)
     

    def getParams(self):
        return dict(urllib.parse.parse_qsl(self.sysARG[2][1:]))


    def run(self):  
        params=self.getParams()
        name    = (urllib.parse.unquote(params.get("name",'')) or None)
        channel = (params.get("channel",'')                    or None)
        url     = (params.get("url",'')                        or None)
        id      = (params.get("id",'')                         or None)
        radio   = (params.get("radio",'')                      or 'False')
        mode    = (params.get("mode",'')                       or None)
        
        log("Name: %s"   %(name))
        log("Channel: %s"%(channel))
        log("URL: %s"    %(url))
        log("ID: %s"     %(id))
        log("Radio: %s"  %(radio))
        log("Mode: %s"   %(mode))
        
        if channel is None:
            if   mode is None: self.buildMenu(name)
            elif mode == 'play':      
                if radio == 'True':
                    self.playRadio(name, id)
                else: 
                    self.playChannel(name, id, isPlaylist=self.usePlaylist)
            elif mode == 'Utilities': self.utilities(name)
            elif mode == 'Channels':  self.channels(name)

        xbmcplugin.setContent(int(self.sysARG[1])    , self.CONTENT_TYPE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(int(self.sysARG[1]), cacheToDisc=self.CACHE_ENABLED)
       
if __name__ == '__main__': Plugin(sys.argv).run()