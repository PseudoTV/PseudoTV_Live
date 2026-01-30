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

from globals    import *
from plugin     import Plugin
from autotune   import Autotune

def _run(sysARG, fitem: dict={}, nitem: dict={}):
    with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
        params = dict(urllib.parse.parse_qsl(sys.argv[2][1:].replace('.pvr','')))
        params['mode']       = params.get("mode")
        params['radio']      = params['mode'] == "radio"
        params['fitem']      = fitem
        params['nitem']      = nitem
        params['vid']        = decodeString(params.get("vid",''))
        params["chid"]       = (params.get("chid")  or fitem.get('citem',{}).get('id'))
        params['title']      = (params.get('title') or BUILTIN.getInfoLabel('label'))
        params['name']       = (unquoteString(params.get("name",'')) or BUILTIN.getInfoLabel('ChannelName'))
        params['isPlaylist'] = bool(SETTINGS.getSettingInt('Playback_Method'))
        log("Default: run, params = %s"%(params))
        
        if   PROPERTIES.isRunning('Tasks.chkPVRRefresh'): DIALOG.notificationDialog(LANGUAGE(32166))
        elif params['mode'] == 'live':
            if params.get('start') == '{utc}' or str(BUILTIN.getInfoLabel('ChannelNumber')) == '0':
                PROPERTIES.setPropTimer('chkPVRRefresh')
                params.update({'start':0,'stop':0,'duration':0})
                if   params['isPlaylist']:        threadit(Plugin(sysARG, sysInfo=params).playPlaylist)(params["name"],params["chid"])
                elif params['vid'] :              threadit(Plugin(sysARG, sysInfo=params).playTV)(params["name"],params["chid"])
            elif params['isPlaylist']:            threadit(Plugin(sysARG, sysInfo=params).playPlaylist)(params["name"],params["chid"])
            elif params['vid']:                   threadit(Plugin(sysARG, sysInfo=params).playLive)(params["name"],params["chid"],params["vid"])
            else:                                 threadit(Plugin(sysARG, sysInfo=params).playTV)(params["name"],params["chid"])
            MONITOR().waitForAbort(float(SETTINGS.getSettingInt('RPC_Delay')/1000)) #delay to avoid thread crashes when fast channel changing ie PVR channel surfing.
        elif params['vid']:
            if   params['mode'] == 'vod':                   threadit(Plugin(sysARG, sysInfo=params).playVOD)(params["title"],params["vid"])
            elif params['mode'] == 'dvr':                   threadit(Plugin(sysARG, sysInfo=params).playDVR)(params["title"],params["vid"])
            elif params['chid']:
                if   mode == 'broadcast':         threadit(Plugin(sysARG, sysInfo=params).playBroadcast)(params["name"],params["chid"],params["vid"])
                elif mode == 'radio':             threadit(Plugin(sysARG, sysInfo=params).playRadio)(params["name"],params["chid"],params["vid"])
        elif params['mode'] == 'resume' and params['chid']: threadit(Plugin(sysARG, sysInfo=params).playPaused)(params["name"],params["chid"])
        else: DIALOG.notificationDialog(LANGUAGE(32000))
        
if __name__ == '__main__':
    mode = dict(urllib.parse.parse_qsl(sys.argv[2][1:].replace('.pvr',''))).get("mode")
    if   mode == 'settings':                        threadit(SETTINGS.openSettings)
    elif mode is None and PROPERTIES.hasChannels(): threadit(SETTINGS.openGuide)
    elif mode is None and SETTINGS.hasAutotuned():  threadit(SETTINGS.autoTune)
    else: threadit(_run)(sys.argv, decodePlot(BUILTIN.getInfoLabel('Plot')), decodePlot(BUILTIN.getInfoLabel('NextPlot')))
    # if SETTINGS.hasAddon(PVR_CLIENT_ID,install=True,enable=True,force=True):