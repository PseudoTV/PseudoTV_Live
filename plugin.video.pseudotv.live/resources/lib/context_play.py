#   Copyright (C) 2026 Lunatixz
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
from variables import *
from plugin    import Plugin
     
@threadit
def _run(sysARG, fitem: dict={}, nitem: dict={}):
    with Globals.builtin.busy_dialog():
        mode                 = sysARG[1]
        params               = {}
        params['fitem']      = fitem
        params['nitem']      = nitem
        params['vid']        = FileAccess._decodeString(params.get("vid",''))
        params["chid"]       = (params.get("chid")  or fitem.get('citem',{}).get('id'))
        params['title']      = (params.get('title') or Globals.builtin.getInfoLabel('ListItem.label'))
        params['name']       = (Globals._unquoteString(params.get("name",'')) or fitem.get('citem',{}).get('name') or Globals.builtin.getInfoLabel('ListItem.ChannelName'))
        params['isPlaylist'] = (mode == 'playlist')
        LOG("Context_Play: _run, params = %s"%(params))
        
        if   mode == 'play':     threadit(Plugin(sysARG, sysInfo=params).playTV)(params["name"],params["chid"])
        elif mode == 'playlist': threadit(Plugin(sysARG, sysInfo=params).playPlaylist)(params["name"],params["chid"])
            
if __name__ == '__main__': _run(sys.argv, Globals._decodePlot(Globals.builtin.getInfoLabel('ListItem.Plot')), Globals._decodePlot(Globals.builtin.getInfoLabel('ListItem.NextPlot')))