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

from globals   import *
from plugin    import Plugin

def run(sysARG, fitem: dict={}, nitem: dict={}):
    params = dict(urllib.parse.parse_qsl(sysARG[2][1:].replace('.pvr','')))
    mode   = (params.get("mode")  or 'guide')
    params['fitem']      = fitem
    params['nitem']      = nitem
    params['vid']        = decodeString(params.get("vid",''))
    params["chid"]       = (params.get("chid")  or fitem.get('citem',{}).get('id'))
    params['title']      = (params.get('title') or BUILTIN.getInfoLabel('label'))
    params['name']       = (unquoteString(params.get("name",'')) or BUILTIN.getInfoLabel('ChannelName'))
    params['isPlaylist'] = bool(SETTINGS.getSettingInt('Playback_Method'))
    log("Default: run, params = %s"%(params))

    if PROPERTIES.isRunning('togglePVR'):   DIALOG.notificationDialog(LANGUAGE(32000))
    elif mode == 'live':
        if   params['isPlaylist']:          threadit(Plugin(sysARG, sysInfo=params).playPlaylist)(params["name"],params["chid"])
        elif params['vid'] :                threadit(Plugin(sysARG, sysInfo=params).playLive)(params["name"],params["chid"],params["vid"])
        else:                               threadit(Plugin(sysARG, sysInfo=params).playTV)(params["name"],params["chid"])
    elif mode in ['vod','dvr']:             threadit(Plugin(sysARG, sysInfo=params).playVOD)(params["title"],params["vid"])
    elif mode == 'broadcast':               threadit(Plugin(sysARG, sysInfo=params).playBroadcast)(params["name"],params["chid"],params["vid"])
    elif mode == 'radio':                   threadit(Plugin(sysARG, sysInfo=params).playRadio)(params["name"],params["chid"],params["vid"])
    elif mode == 'guide'                and hasAddon(PVR_CLIENT_ID,install=True,enable=True): SETTINGS.openGuide()
    elif mode == 'settings'             and hasAddon(PVR_CLIENT_ID,install=True,enable=True): SETTINGS.openSettings()
    else:                                   DIALOG.notificationDialog(LANGUAGE(32000))
    
if __name__ == '__main__': run(sys.argv,fitem=decodePlot(BUILTIN.getInfoLabel('Plot')),nitem=decodePlot(BUILTIN.getInfoLabel('NextPlot')))