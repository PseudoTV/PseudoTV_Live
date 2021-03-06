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

from resources.lib.globals  import *
from resources.lib.rules    import RulesList

class Plugin:
    def __init__(self, sysARG=sys.argv, service=None):
        self.log('__init__, sysARG = ' + str(sysARG))
        self.sysARG         = sysARG
        self.CONTENT_TYPE   = 'episodes'
        self.CACHE_ENABLED  = True
        self.ruleList       = {}
        self.playlist       = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        
        self.rules          = RulesList()
        if service is None:
            from resources.lib.jsonrpc import JSONRPC
            self.jsonRPC    = JSONRPC()
            self.myPlayer   = MY_PLAYER
        else:
            self.jsonRPC    = service.jsonRPC
            self.myPlayer   = service.myPlayer
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def runActions(self, action, citem, parameter=None):
        self.log("runActions action = %s, channel = %s"%(action,citem))
        if not citem.get('id',''): return parameter
        ruleList = self.ruleList.get(citem['id'],[])
        for rule in ruleList:
            if action in rule.actions:
                self.log("runActions performing channel rule: %s"%(rule.name))
                parameter = rule.runAction(action, self, parameter)
        return parameter


    def buildMenu(self, name=None):
        self.log('buildMenu, name = %s'%name)
        MAIN_MENU = [(LANGUAGE(30008), '', '')]#"Channels"

        UTIL_MENU = [#(LANGUAGE(30010), '', '', LANGUAGE(30008)),#"Rebuild M3U/XMLTV"
                     (LANGUAGE(30011), '', '', LANGUAGE(30008)),#"Delete [M3U/XMLTV/Genre]"
                     (LANGUAGE(30096), '', '', LANGUAGE(30008)),#"Clean Start, Delete [Channels/Settings/M3U/XMLTV/Genre]"
                     (LANGUAGE(30012)%(getPluginMeta(PVR_CLIENT).get('name',''),ADDON_NAME,), '', '', LANGUAGE(30008)), #"Reconfigure PVR for use with PTVL"
                     (LANGUAGE(30065)%(getPluginMeta(PVR_CLIENT).get('name','')), '', '', LANGUAGE(30008)),#"Force PVR reload"
                     (LANGUAGE(30013), '', '', LANGUAGE(30008))]#"Open Settings"

        if   name is None:            items = MAIN_MENU
        elif name == LANGUAGE(30008): items = UTIL_MENU
        else: return
        [self.addDir(*item) for item in items]
        
        
    def deleteFiles(self, msg, full=False):
        self.log('deleteFiles, full = %s'%(full))
        setBusy(True)
        files = {LANGUAGE(30172):M3UFLE,LANGUAGE(30173):XMLTVFLE,LANGUAGE(30009):CHANNELFLE,LANGUAGE(30130):SETTINGS_FLE,LANGUAGE(30179):LIBRARYFLE}
        keys  = [LANGUAGE(30172),LANGUAGE(30173),LANGUAGE(30009),LANGUAGE(30130),LANGUAGE(30179)]
        if not full: keys = keys[:3]
        if yesnoDialog('%s ?'%(msg)): [notificationDialog(LANGUAGE(30016)%(key)) for key in keys if FileAccess.delete(files[key])]
        setPropertyBool('pendingChange',True)
        setPropertyBool('autotuned',False)
        if full: return okDialog(LANGUAGE(30183))
        setBusy(False)
        return True

            
    def utilities(self, name):
        self.log('utilities, name = %s'%name)
        with busy():
            if   name == LANGUAGE(30011): self.deleteFiles(name)
            elif name == LANGUAGE(30096): self.deleteFiles(name, full=True)
            elif name == LANGUAGE(30012)%(getPluginMeta(PVR_CLIENT).get('name',''),ADDON_NAME,): configurePVR()
            elif name == LANGUAGE(30065)%(getPluginMeta(PVR_CLIENT).get('name','')): brutePVR()
            elif name == LANGUAGE(30013): REAL_SETTINGS.openSettings()
            else: return
        xbmc.executebuiltin('Action(Back,10025)')
            

    def addLink(self, name, channel, path, mode='',icon=ICON, liz=None, total=0):
        if liz is None:
            liz=xbmcgui.ListItem(name)
            liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
            liz.setArt({'thumb':icon,'logo':icon,'icon':icon})
        self.log('addLink, name = %s'%(name))
        u=self.sysARG[0]+"?url="+urllib.parse.quote(path)+"&channel="+str(channel)+"&name="+urllib.parse.quote(name)+"&mode="+str(mode)
        xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,totalItems=total)


    def addDir(self, name, channel, path, mode='',icon=ICON, liz=None):
        self.log('addDir, name = %s'%(name))
        if liz is None:
            liz=xbmcgui.ListItem(name)
            liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
            liz.setArt({'thumb':icon,'logo':icon,'icon':icon})
        liz.setProperty('IsPlayable', 'false')
        u=self.sysARG[0]+"?url="+urllib.parse.quote(path)+"&channel="+str(channel)+"&name="+urllib.parse.quote(name)+"&mode="+str(mode)
        xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,isFolder=True)
     

    def contextPlay(self, writer, isPlaylist=False):
        channelData = writer.get('citem',{}) 
        if channelData: 
            stpos   = 0
            pvritem = self.jsonRPC.getPVRposition(channelData.get('name',''), channelData.get('id',''), isPlaylist=isPlaylist)
            self.log('contextPlay, writer = %s, pvritem = %s, isPlaylist = %s'%(writer,pvritem,isPlaylist))
            self.playlist.clear()
            xbmc.sleep(100)
            
            if isPlaylist:
                nowitem = pvritem.get('broadcastnow',{})
                liz = buildItemListItem(getWriter(nowitem.get('writer','')))
                liz.setProperty('pvritem', dumpJSON(pvritem))
                setCurrentChannelItem(pvritem)
                
                listitems = [liz]
                nextitems = pvritem.get('broadcastnext',[])[slice(0, PAGE_LIMIT)] # list of upcoming items, truncate for speed.
                listitems.extend([buildItemListItem(getWriter(nextitem.get('writer',''))) for nextitem in nextitems])
                nextitems.insert(0,nowitem)
                
                for pos, nextitem in enumerate(nextitems):
                    if getWriter(nextitem.get('writer',{})).get('file','') == writer.get('file',''):
                        stpos = pos
                        break
            else:
                liz = buildItemListItem(writer)
                liz.setProperty('pvritem', dumpJSON(pvritem))
                setCurrentChannelItem(pvritem)
                
                listitems = [liz]
                stpos = 0
                
            self.log('contextPlay, writer stpos = %s, playlist = %s'%(stpos,len(listitems)))
            [self.playlist.add(lz.getPath(),lz,idx) for idx,lz in enumerate(listitems)]
            if isPlaylistRandom(): self.playlist.unshuffle()
            return self.myPlayer.play(self.playlist, startpos=stpos)

        notificationDialog(LANGUAGE(30001))
        return xbmcplugin.setResolvedUrl(int(self.sysARG[1]), False, xbmcgui.ListItem())
        
        
    def playRadio(self, name, id):
        self.log('playRadio, id = %s'%(id))
        pvritem = self.jsonRPC.getPVRposition(name, id, radio=True)
        nowitem = pvritem.get('broadcastnow',{}) # current item
        
        if nowitem:
            writer   = getWriter(nowitem.get('writer',{}))
            response = self.jsonRPC.requestList(id, writer.get('citem',{}).get('path',''), 'music', page=RADIO_ITEM_LIMIT)
            if response:
                self.playlist.clear()
                xbmc.sleep(100)
                
                nextitems = response
                random.shuffle(nextitems)
                nowitem   = nextitems.pop(0)
                
                liz = buildItemListItem(nowitem, mType='music')
                liz.setProperty('pvritem', dumpJSON(pvritem))
                setCurrentChannelItem(pvritem)
                
                listitems = [liz]
                listitems.extend([buildItemListItem(nextitem, mType='music') for nextitem in nextitems])
                [self.playlist.add(lz.getPath(),lz,idx) for idx,lz in enumerate(listitems)]
                if not isPlaylistRandom(): self.playlist.shuffle()
                self.log('playRadio, Playlist size = %s'%(self.playlist.size()))
                return self.myPlayer.play(self.playlist)

        notificationDialog(LANGUAGE(30001))
        return xbmcplugin.setResolvedUrl(int(self.sysARG[1]), False, xbmcgui.ListItem())
            
        
    def playChannel(self, name, id, isPlaylist=False, failed=False):
        self.log('playChannel, id = %s, isPlaylist = %s'%(id,isPlaylist))
        found     = False
        listitems = [xbmcgui.ListItem()] #empty listitem required to pass failed playback.
        pvritem   = self.jsonRPC.getPVRposition(name, id, isPlaylist=isPlaylist)
        nowitem   = pvritem.get('broadcastnow',{}) # current item
        nextitems = pvritem.get('broadcastnext',[])[slice(0, PAGE_LIMIT)] # list of upcoming items, truncate for speed.

        if nowitem:
            found         = True
            setOffset     = False
            citem         = getWriter(nowitem.get('writer',{})).get('citem',{})
            self.ruleList = self.rules.loadRules([citem])
            nowitem       = self.runActions(RULES_ACTION_PLAYBACK, citem, nowitem)
            progress      = nowitem['progress']
            runtime       = nowitem['runtime']
            self.log('playChannel, nowitem = %s'%(nowitem))
            self.playlist.clear()
            
            if (progress > getSettingInt('Seek_Tolerance')):
                # seekThreshold = int((runtime * 60) - getSettingInt('Seek_Threshold'))
                # self.log('playChannel, progress = %s, seekThreshold = %s'%(progress,seekThreshold))
                if (nowitem['progresspercentage'] >= float(getSettingInt('Seek_Threshold%'))):  # near end, avoid callback; override nowitem and queue next show.
                    self.log('playChannel, progress near the end, queue nextitem')
                    nowitem = nextitems.pop(0) #remove first element in nextitems keep playlist order.
                else: setOffset = True
                    
            writer = getWriter(nowitem.get('writer',{}))
            liz = buildItemListItem(writer)
            liz.setProperty('pvritem', dumpJSON(pvritem))
            
            if setOffset:
                self.log('playChannel, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((runtime * 60),progress))
                pvritem['progress'] = progress
                pvritem['runtime']  = runtime
                liz.setProperty('totaltime'  , str((runtime * 60))) #sec
                liz.setProperty('resumetime' , str(progress)) #sec
                liz.setProperty('startoffset', str(progress)) #sec
                
                url  = liz.getPath()
                file = writer.get('originalfile','')
                if url.startswith('stack://') and not url.startswith('stack://%s'%(file)):
                    self.log('playChannel, playing stack with url = %s'%(url))
                    #remove pre-roll stack from seek offset video.
                    liz.setPath('stack://%s'%(' , '.join(stripStack(file, url))))

            listitems = [liz]
            setCurrentChannelItem(pvritem)
            
            if isPlaylist: 
                listitems.extend([buildItemListItem(getWriter(nextitem.get('writer',''))) for nextitem in nextitems])
                [self.playlist.add(lz.getPath(),lz,idx) for idx,lz in enumerate(listitems)]
                if isPlaylistRandom(): self.playlist.unshuffle()
                self.log('playChannel, Playlist size = %s'%(self.playlist.size()))
                return self.myPlayer.play(self.playlist)  
        else: notificationDialog(LANGUAGE(30001))
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitems[0])


    def playVOD(self, name, id):
        path = decodeString(id)
        self.log('playVOD, path = %s'%(path))
        liz = xbmcgui.ListItem(name,path=path)
        liz.setProperty("IsPlayable","true")
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)


    def getParams(self):
        return dict(urllib.parse.parse_qsl(self.sysARG[2][1:]))


    def run(self):  
        params  = self.getParams()
        name    = (urllib.parse.unquote(params.get("name",'')) or None)
        channel = (params.get("channel",'')                    or None)
        url     = (params.get("url",'')                        or None)
        id      = (params.get("id",'')                         or None)
        radio   = (params.get("radio",'')                      or 'False') == "True"
        mode    = (params.get("mode",'')                       or None)
        self.log("Name = %s, Channel = %s, URL = %s, ID = %s, Radio = %s, Mode = %s"%(name,channel,url,id,radio,mode))

        if   mode is None:  self.buildMenu(name)
        elif mode == 'vod': self.playVOD(name, id)
        elif mode == 'play':
            if radio:
                self.playRadio(name, id)
            else:
                self.playChannel(name, id, isPlaylist=bool(getSettingInt('Playback_Method')))
        elif mode == 'Utilities': self.utilities(name)

        xbmcplugin.setContent(int(self.sysARG[1])    , self.CONTENT_TYPE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(int(self.sysARG[1]) , xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(int(self.sysARG[1]), cacheToDisc=self.CACHE_ENABLED)
       
if __name__ == '__main__': Plugin(sys.argv).run()