#   Copyright (C) 2023 Lunatixz
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

class Info:
    def __init__(self, sysARG, writer):
        with busy_dialog():
            log('Info: __init__, sysARG = %s'%(sysARG))
            listitem = LISTITEMS.buildItemListItem(writer)
        DIALOG.infoDialog(listitem)
            
class Browse:
    def __init__(self, sysARG, writer):
        log('Browse: __init__, sysARG = %s'%(sysARG))
        with busy_dialog():
            target  = '%ss'%(writer.get('media','video'))
            orgpath = writer.get('originalpath','')
            citem   = Builder().buildProvisional(writer.get('citem',{}))

            if '?xsp=' in orgpath:
                path, params = orgpath.split('?xsp=')
                path = '%s?xsp=%s'%(path,quoteString(unquoteString(params)))
            elif citem.get('provisional',None):
                #todo build xsp with path rule.
                provisional = citem.get('provisional',{})
                path        = provisional.get('path',[])
            else: 
                path = citem.get('path','')
            if isinstance(path,list): path = path[0]
            
        log('Browse: target = %s, path = %s'%(target,path))
        BUILTIN.executebuiltin('ReplaceWindow(%s,%s)'%(target,path))

class Match:
    SEARCH_SCRIPT  = None
    GLOBAL_SCRIPT  = 'script.globalsearch'
    SIMILAR_SCRIPT = 'script.embuary.helper'

    def __init__(self, sysARG):
        with busy_dialog():
            title  = BUILTIN.getInfoLabel('Title')
            name   = BUILTIN.getInfoLabel('EpisodeName')
            writer = decodeWriter(BUILTIN.getInfoLabel('Writer'))
            dbtype = writer.get('type').replace('episodes','tvshow').replace('tvshows','tvshow').replace('movies','movie')
            dbid   = (writer.get('tvshowid') or writer.get('movieid'))
            log('Match: __init__, sysARG = %s, title = %s, dbtype = %s, dbid = %s'%(sysARG,'%s - %s'%(title,name),dbtype,dbid))

        if hasAddon(self.SIMILAR_SCRIPT,install=True) and dbid:
            self.SEARCH_SCRIPT = self.SIMILAR_SCRIPT
        elif hasAddon(self.GLOBAL_SCRIPT,install=True):
            self.SEARCH_SCRIPT = self.GLOBAL_SCRIPT
        else: return DIALOG.notificationDialog(LANGUAGE(32000))
        log('Match: SEARCH_SCRIPT = %s'%(self.SEARCH_SCRIPT))
        hasAddon(self.SEARCH_SCRIPT,enable=True)

        if self.SEARCH_SCRIPT == self.SIMILAR_SCRIPT:
            # plugin://script.embuary.helper/?info=getsimilar&dbid=$INFO[ListItem.DBID]&type=tvshow&tag=HDR
            # plugin://script.embuary.helper/?info=getsimilar&dbid=$INFO[ListItem.DBID]&type=movie&tag=HDR
            # tag = optional, additional filter option to filter by library tag
            BUILTIN.executebuiltin('ReplaceWindow(%s,%s)'%('%ss'%(writer.get('media','video')),'plugin://%s/?info=getsimilar&dbid=%d&type=%s'%(self.SEARCH_SCRIPT,dbid,dbtype)))
        else:
            # - the addon is executed by another addon/skin: RunScript(script.globalsearch,searchstring=foo)
            # You can specify which categories should be searched (this overrides the user preferences set in the addon settings):
            # RunScript(script.globalsearch,movies=true)
            # RunScript(script.globalsearch,tvshows=true&amp;musicvideos=true&amp;songs=true)
            # availableeoptions: movies, tvshows, episodes, musicvideos, artists, albums, songs, livetv, actors, directors
            BUILTIN.executebuiltin('RunScript(%s)'%('%s,searchstring=%s'%(self.SEARCH_SCRIPT,escapeString('%s,movies=True,episodes=True,tvshows=True,livetv=True'%(quoteString(title))))))
 

if __name__ == '__main__': 
    try:    param = sys.argv[1]
    except: param = None
    log('Info: __main__, param = %s'%(param))
    if param == 'info':
        Info(sys.argv,writer=decodeWriter(BUILTIN.getInfoLabel('Writer')))
    elif param == 'browse':
        from builder   import Builder
        Browse(sys.argv,writer=decodeWriter(BUILTIN.getInfoLabel('Writer')))
    elif param == 'match':
        Match(sys.argv)
   