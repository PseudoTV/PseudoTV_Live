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

class Match:
    def __init__(self, sysARG):
        log('Match: __init__, sysARG = %s'%(sysARG))
        title  = BUILTIN.getInfoLabel('Title')
        name   = BUILTIN.getInfoLabel('EpisodeName')
        search = '%s,movies=True,episodes=True,tvshows=True,livetv=True'%(quoteString(title))
        path   = 'script.globalsearch,searchstring=%s'%(escapeString(search))
        log('Match: path = %s'%(path))
        if not BUILTIN.getInfoBool('HasAddon(script.globalsearch)','System'):
            BUILTIN.executebuiltin('InstallAddon(script.globalsearch)')
        BUILTIN.executebuiltin('RunScript(%s)'%(path))

        # - the addon is executed by another addon/skin: RunScript(script.globalsearch,searchstring=foo)
        # You can specify which categories should be searched (this overrides the user preferences set in the addon settings):
        # RunScript(script.globalsearch,movies=true)
        # RunScript(script.globalsearch,tvshows=true&amp;musicvideos=true&amp;songs=true)
        # availableeoptions: movies, tvshows, episodes, musicvideos, artists, albums, songs, livetv, actors, directors
    
if __name__ == '__main__': 
    Match(sys.argv)
# plugin://script.embuary.helper/?info=getsimilar&dbid=$INFO[ListItem.DBID]&type=movie
# plugin://script.embuary.helper/?info=getsimilar&dbid=$INFO[ListItem.DBID]&type=tvshow



