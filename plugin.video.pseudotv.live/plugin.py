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

from globals import *
from builder import Builder

class Plugin:
    def __init__(self, sysARG):
        log('__init__, sysARG = ' + str(sysARG))
        self.sysARG = sysARG
        self.CONTENT_TYPE  = 'episodes'
        self.CACHE_ENABLED = False
        self.myBuilder = Builder()
        self.myBuilder.plugin = self
        self.playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.maxDays  = getSettingInt('Max_Days')
        self.seekTol  = getSettingInt('Seek_Tolerence')
        self.usePlaylist = bool(getSettingInt('Playback_Method'))
        
        
    def buildMenu(self, name=None):
        log('buildMenu, name = %s'%name)
        MAIN_MENU = [(LANGUAGE(30008), '', '')]#,#todo
                     # (LANGUAGE(30009), '', '')]

        UTIL_MENU = [(LANGUAGE(30010), '', '', LANGUAGE(30008)),
                     (LANGUAGE(30011), '', '', LANGUAGE(30008)),
                     (LANGUAGE(30012), '', '', LANGUAGE(30008)),
                     (LANGUAGE(30065), '', '', LANGUAGE(30008)),                     
                     (LANGUAGE(30013), '', '', LANGUAGE(30008))]

        CHAN_MENU = [(LANGUAGE(30014), '', '', LANGUAGE(30009)),
                     (LANGUAGE(30015), '', '', LANGUAGE(30009))]

        if   name is None:            items = MAIN_MENU
        elif name == LANGUAGE(30008): items = UTIL_MENU
        elif name == LANGUAGE(30009): items = CHAN_MENU
        else: return
        [self.addDir(*item) for item in items]
        
        
    def deleteFiles(self):
        log('utilities, deleteFiles')
        if yesnoDialog(LANGUAGE(30057)):
            [func() for func in [self.myBuilder.m3u.delete,self.myBuilder.xmltv.delete,self.myBuilder.xmltv.delete]]
        
        
        
    def utilities(self, name):
        log('utilities, name = %s'%name)
        if name   == LANGUAGE(30010): self.myBuilder.buildService(reloadPVR=True)
        elif name == LANGUAGE(30011): self.deleteFiles()
        elif name == LANGUAGE(30012): configurePVR()
        elif name == LANGUAGE(30065): brutePVR()
        elif name == LANGUAGE(30013): REAL_SETTINGS.openSettings()
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


    def isPlaylistRandom(self):
        return xbmc.getInfoLabel('Playlist.Random').lower() == 'random' # Disable auto playlist shuffling if it's on
        
        
    def isPlaylistRepeat(self):
        return xbmc.getInfoLabel('Playlist.IsRepeat').lower() == 'true' # Disable auto playlist repeat if it's on #todo


    def play(self, pvritem, isPlaylist=False):
        log('play, pvritem = %s, isPlaylist = %s'%(pvritem,isPlaylist))
        file = loadJSON(pvritem.replace(' /  "',' , "').replace(' /  ',', ')).get('file','') # current item
        if not file: return
        xbmc.executebuiltin('PlayMedia(%s)'%file)
            # liz       = xbmcgui.ListItem()
            # listitems = [liz]
            # liz = buildItemListItem(pvritem)
            # liz.setPath(file)
            # listitems = [liz]
            # self.playlist.clear()
            # xbmc.sleep(100)
            # [self.playlist.add(lz.getPath(),lz,idx) for idx,lz in enumerate(listitems)]
            # if self.isPlaylistRandom(): self.playlist.unshuffle()
            # return xbmc.Player().play(self.playlist)
    
        
    def playChannel(self, name, id, isPlaylist=False, failed=False):
        log('playChannel, id = %s, isPlaylist = %s'%(id,isPlaylist))
        found = False
        liz       = xbmcgui.ListItem()
        listitems = [liz]
        pvritem   = self.myBuilder.jsonRPC.getPVRposition(name, id, isPlaylist)
        # pvritem['callback'] = self.myBuilder.jsonRPC.matchPVRPath(pvritem.get('channelid','')) # move to service?
        nowitem   = pvritem.get('broadcastnow',{}) # current item
        ruleslist = []#check pre-play channel rules.
        
        if nowitem:
            found = True
            setCurrentChannelItem(pvritem)
            liz = buildItemListItem(loadJSON(nowitem.get('writer',{})))
            
            if nowitem['progress'] >= self.seekTol:
                liz.setProperty('totaltime', str((nowitem['runtime'] * 60)))
                liz.setProperty('resumetime', str(nowitem['progress']))
                liz.setProperty('startoffset', str(nowitem['progress']))
            listitems = [liz]
                
            if isPlaylist: 
                self.playlist.clear()
                xbmc.sleep(100)
                
                nextitems = pvritem.get('broadcastnext',[])[slice(0, self.maxDays)] # list of upcoming items, truncate for speed.
                lastitem  = nextitems[-1]
                nextitems.pop(-1)
                lastwriter = loadJSON(lastitem['writer'])
                lastwriter['file'] = pvritem['callback'] #create a callback on last playlist element to callback plugin.
                lastitem['writer'] = dumpJSON(lastwriter)
                nextitems.append(lastitem)
                listitems.extend([buildItemListItem(loadJSON(nextitem.get('writer',''))) for nextitem in nextitems]) 
                [self.playlist.add(lz.getPath(),lz,idx) for idx,lz in enumerate(listitems)]
                
                if self.isPlaylistRandom(): self.playlist.unshuffle()
                return xbmc.Player().play(self.playlist)
                
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitems[0])
                
        # elif not failed:
            # notificationDialog(LANGUAGE(30058))
            # return self.playChannel(name, id, isPlaylist, failed=True)
        # else:
            # notificationDialog(LANGUAGE(30059))
            # return brutePVR()
            
        
        
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
        try:    name=urllib.parse.unquote(params["name"])
        except: name=None
        try:    channel=int(params["channel"])
        except: channel=None
        try:    url=urllib.parse.unquote(params["url"])
        except: url=None
        try:    id=urllib.parse.unquote(params["id"])
        except: id=None
        try:    mode=urllib.parse.unquote(params["mode"])
        except: mode=None
        log("Channel: "+str(channel))
        log("Name: "+str(name))
        log("URL: "+str(url))
        log("ID: "+str(id))
        log("Mode: "+str(mode))
        
        if channel is None:
            if   mode is None: self.buildMenu(name)
            elif mode == 'play':      self.playChannel(name, id, isPlaylist=self.usePlaylist)
            elif mode == 'Utilities': self.utilities(name)
            elif mode == 'Channels':  self.channels(name)

        xbmcplugin.setContent(int(self.sysARG[1])    , self.CONTENT_TYPE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(int(self.sysARG[1]), cacheToDisc=self.CACHE_ENABLED)
       
if __name__ == '__main__': Plugin(sys.argv).run()