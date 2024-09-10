#   Copyright (C) 2024 Lunatixz
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
from plugin  import Plugin
     
def run(sysARG):
    params = {}
    log("Context_Play: run, In params = %s"%(params))
    params['radio']      = (params.get("radio") or 'False').lower() == "true"
    params['chnumlabel'] = BUILTIN.getInfoLabel('ChannelNumberLabel')
    params['name']       = (unquoteString(params.get("name",''))  or BUILTIN.getInfoLabel('ChannelName'))
    params['title']      = (unquoteString(params.get("title",'')) or BUILTIN.getInfoLabel('label'))
    params['duration']   = int((params.get('duration')            or timeString2Seconds(BUILTIN.getInfoLabel('Duration(hh:mm:ss)')) or '0'))
    params['vid']        = (decodeString(params.get("vid",'')     or None))
    params['chpath']     = BUILTIN.getInfoLabel('FileNameAndPath')
    params['fitem']      = decodePlot(BUILTIN.getInfoLabel('Plot'))
    params['nitem']      = decodePlot(BUILTIN.getInfoLabel('NextPlot'))
    params['citem']      = params.get('fitem',{}).get('citem',{})
    params["chid"]       = params.get('citem',{}).get('id')
    params['playcount']  = 0
    params['isLinear']   = True if sysARG[1] == 'live' else False
    params['isPlaylist'] = bool(SETTINGS.getSettingInt('Playback_Method'))
    params['progress']   = (int((BUILTIN.getInfoLabel('Progress') or '0')),int((BUILTIN.getInfoLabel('PercentPlayed') or '0')))
    params['now']        = int(params.get('now') or getUTCstamp())
    log("Context_Play: run, Out params = %s"%(params))
    
    if   sysARG[1] == 'play':     threadit(Plugin(sysARG, sysInfo=params).playTV)(params["name"],params["chid"])
    elif sysARG[1] == 'playlist': threadit(Plugin(sysARG, sysInfo=params).playPlaylist)(params["name"],params["chid"])
        
if __name__ == '__main__': run(sys.argv)

