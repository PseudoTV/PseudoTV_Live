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

SEARCH_SCRIPT  = None
GLOBAL_SCRIPT  = 'script.globalsearch'
SIMILAR_SCRIPT = 'script.embuary.helper'

class Match:
    def __init__(self, sysARG):
        title  = BUILTIN.getInfoLabel('Title')
        name   = BUILTIN.getInfoLabel('EpisodeName')
        writer = decodeWriter(BUILTIN.getInfoLabel('Writer'))
        dbtype = writer.get('type').replace('episodes','tvshow').replace('tvshows','tvshow').replace('movies','movie')
        dbid   = (writer.get('tvshowid') or writer.get('movieid'))
        log('Match: __init__, sysARG = %s, title = %s, dbtype = %s, dbid = %s'%(sysARG,'%s - %s'%(title,name),dbtype,dbid))

        if BUILTIN.getInfoBool('HasAddon(%s)'%(SIMILAR_SCRIPT),'System') and dbid:
            SEARCH_SCRIPT = SIMILAR_SCRIPT
        elif BUILTIN.getInfoBool('HasAddon(%s)'%(GLOBAL_SCRIPT),'System'):
            SEARCH_SCRIPT = GLOBAL_SCRIPT
        else: return DIALOG.notificationDialog(LANGUAGE(32000))
        
        if BUILTIN.getInfoBool('HasAddon(%s)'%(SEARCH_SCRIPT),'System'):
            if not BUILTIN.getInfoBool('AddonIsEnabled(%s)'%(SEARCH_SCRIPT),'System'):
                BUILTIN.executebuiltin('EnableAddon(%s)'%(SEARCH_SCRIPT))
        else:
            BUILTIN.executebuiltin('InstallAddon(%s)'%(SEARCH_SCRIPT))

        if SEARCH_SCRIPT == SIMILAR_SCRIPT:
            # plugin://script.embuary.helper/?info=getsimilar&dbid=$INFO[ListItem.DBID]&type=tvshow&tag=HDR
            # plugin://script.embuary.helper/?info=getsimilar&dbid=$INFO[ListItem.DBID]&type=movie&tag=HDR
            # tag = optional, additional filter option to filter by library tag
            BUILTIN.executebuiltin('ActivateWindow(%s,%s,return)'%('%ss'%(writer.get('media','video')),'plugin://%s/?info=getsimilar&dbid=%d&type=%s'%(SEARCH_SCRIPT,dbid,dbtype)))
        else:
            # - the addon is executed by another addon/skin: RunScript(script.globalsearch,searchstring=foo)
            # You can specify which categories should be searched (this overrides the user preferences set in the addon settings):
            # RunScript(script.globalsearch,movies=true)
            # RunScript(script.globalsearch,tvshows=true&amp;musicvideos=true&amp;songs=true)
            # availableeoptions: movies, tvshows, episodes, musicvideos, artists, albums, songs, livetv, actors, directors
            BUILTIN.executebuiltin('RunScript(%s)'%('%s,searchstring=%s'%(SEARCH_SCRIPT,escapeString('%s,movies=True,episodes=True,tvshows=True,livetv=True'%(quoteString(title))))))
 
if __name__ == '__main__': Match(sys.argv)



