#   Copyright (C) 2025 Lunatixz
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
from variables    import *
from seasonal   import Seasonal 

class Info(object):
    def __init__(self, sysARG: dict={}, listitem: xbmcgui.ListItem=xbmcgui.ListItem(), fitem: dict={}):
        with Globals.builtin.busy_dialog():
            LOG('Info: __init__, sysARG = %s'%(sysARG))
            listitem = Globals.listitems.buildItemListItem(fitem,fitem.get('media','video'))
        Globals.dialog.infoDialog(listitem)
            
class Browse(object): #todo fix with proper container and window
    def __init__(self, sysARG: dict={}, listitem: xbmcgui.ListItem=xbmcgui.ListItem(), fitem: dict={}):
        LOG('Browse: __init__, sysARG = %s'%(sysARG))
        # def __buildMenuItem(item):
            # media = 'music' if item.get('citem',{}).get('radio',False) else 'video'
            # return Globals.listitems.buildItemListItem(item, media)
            
        # with Globals.builtin.busy_dialog():
            # from jsonrpc import JSONRPC
            # print('Browse fitem',fitem)
            # citem = fitem.get('citem',{})
            # items = JSONRPC().matchChannel(citem.get('name'),citem.get('id'),citem.get('radio'))
            # items.get('broadcastnext',[]).insert(0,items.get('broadcastnow'))
            # listitems = poolit(__buildMenuItem)(items)

            # # path  = fitem.get('citem',{}).get('path')
            # # if isinstance(path,list): path = path[0]
            # # if '?xsp=' in path:
                # # path, params = path.split('?xsp=')
                # # path = '%s?xsp=%s'%(path,Globals._quoteString(Globals._unquoteString(params)))
            # LOG('Browse: target = %s, path = %s'%('videos',path))
        # Globals.builtin.executewindow('ReplaceWindow(%s,%s,return)'%('videos',path))
        Globals.dialog.notificationDialog(LANGUAGE(32020))

class Match(object):
    SEARCH_SCRIPT  = None
    GLOBAL_SCRIPT  = 'script.globalsearch'
    EMBUARY_HELPER = 'script.embuary.helper'
    
    def __init__(self, sysARG: dict={}, listitem: xbmcgui.ListItem=xbmcgui.ListItem(), fitem: dict={}):
        with Globals.builtin.busy_dialog():
            title  = Globals.builtin.getInfoLabel('ListItem.Title')
            name   = Globals.builtin.getInfoLabel('ListItem.EpisodeName')
            dbtype = fitem.get('type').replace('episodes','tvshow').replace('tvshows','tvshow').replace('movies','movie')
            dbid   = (fitem.get('tvshowid') or fitem.get('movieid'))
            LOG('Match: __init__, sysARG = %s, title = %s, dbtype = %s, dbid = %s'%(sysARG,'%s - %s'%(title,name),dbtype,dbid))
           
            if Globals.settings.hasAddon(self.GLOBAL_SCRIPT):
                self.SEARCH_SCRIPT = self.GLOBAL_SCRIPT
            elif Globals.settings.hasAddon(self.EMBUARY_HELPER) and dbid:
                self.SEARCH_SCRIPT = self.EMBUARY_HELPER
            else: 
                Globals.dialog.notificationDialog(LANGUAGE(32000))
            LOG('Match: SEARCH_SCRIPT = %s'%(self.SEARCH_SCRIPT))
            Globals.settings.hasAddon(self.SEARCH_SCRIPT)

        if self.SEARCH_SCRIPT == self.EMBUARY_HELPER:
            # plugin://script.embuary.helper/?info=getsimilar&dbid=$INFO[ListItem.DBID]&type=tvshow&tag=HDR
            # plugin://script.embuary.helper/?info=getsimilar&dbid=$INFO[ListItem.DBID]&type=movie&tag=HDR
            # tag = optional, additional filter option to filter by library tag
            Globals.builtin.executewindow('ReplaceWindow(%s,%s,return)'%('%ss'%(fitem.get('media','video')),'plugin://%s/?info=getsimilar&dbid=%d&type=%s'%(self.SEARCH_SCRIPT,dbid,dbtype)))
        else:
            # - the addon is executed by another addon/skin: RunScript(script.globalsearch,searchstring=foo)
            # You can specify which categories should be searched (this overrides the user preferences set in the addon settings):
            # RunScript(script.globalsearch,movies=true)
            # RunScript(script.globalsearch,tvshows=true&amp;musicvideos=true&amp;songs=true)
            # availableeoptions: movies, tvshows, episodes, musicvideos, artists, albums, songs, livetv, actors, directors
            Globals.builtin.executebuiltin('RunScript(%s)'%('%s,searchstring=%s'%(self.SEARCH_SCRIPT,Globals._escapeString('%s,movies=True,episodes=True,tvshows=True,livetv=True'%(Globals._quoteString(title))))))
 

if __name__ == '__main__': 
    param = sys.argv[1]
    LOG('Info: __main__, param = %s'%(param))
    if   param == 'info':   threadit(Info)(sys.argv ,sys.listitem,Globals._decodePlot(Globals.builtin.getInfoLabel('ListItem.Plot')))
    elif param == 'browse': threadit(Browse)(sys.argv,sys.listitem,Globals._decodePlot(Globals.builtin.getInfoLabel('ListItem.Plot')))
    elif param == 'match':  threadit(Match)(sys.argv ,sys.listitem,Globals._decodePlot(Globals.builtin.getInfoLabel('ListItem.Plot')))
        
   
   