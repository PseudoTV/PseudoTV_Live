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

from globals   import *
from plugin    import Plugin

def _run(sysARG, fitem: dict={}, nitem: dict={}):
    """
    Main entry point for PseudoTV Live's functionality.

    Processes system arguments from Kodi and determines the mode of operation,
    including live TV, VOD, DVR, radio, guide, settings, etc. Calls the appropriate
    Plugin functions based on mode and parameters.

    Args:
        sysARG (list): System arguments passed by Kodi.
        fitem (dict, optional): Data about the current item (featured/program). Default empty dict.
        nitem (dict, optional): Data about the next item (upcoming/program). Default empty dict.

    Returns:
        None

    Side Effects:
        - Initiates playback, guide, or settings depending on mode.
        - Displays notifications for unsupported modes or errors.
        - Uses threading for playback functions.
        - Suspends/resumes Kodi activity appropriately.
        - Delays to avoid thread crashes during fast channel changes.

    """
    with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
        params = dict(urllib.parse.parse_qsl(sysARG[2][1:].replace('.pvr','')))
        mode = (params.get("mode") or 'guide')
        params['mode']       = mode
        params['radio']      = mode == "radio"
        params['fitem']      = fitem
        params['nitem']      = nitem
        params['vid']        = decodeString(params.get("vid",''))
        params["chid"]       = (params.get("chid")  or fitem.get('citem',{}).get('id'))
        params['title']      = (params.get('title') or BUILTIN.getInfoLabel('label'))
        params['name']       = (unquoteString(params.get("name",'')) or BUILTIN.getInfoLabel('ChannelName'))
        params['isPlaylist'] = bool(SETTINGS.getSettingInt('Playback_Method'))
        log("Default: run, params = %s"%(params))
        
        if   PROPERTIES.isRunning('Tasks.chkPVRRefresh'): DIALOG.notificationDialog(LANGUAGE(32166))
        elif mode == 'live':
            if params.get('start') == '{utc}' or str(BUILTIN.getInfoLabel('ChannelNumber')) == '0':
                PROPERTIES.setPropTimer('chkPVRRefresh')
                params.update({'start':0,'stop':0,'duration':0})
                if   params['isPlaylist']:      threadit(Plugin(sysARG, sysInfo=params).playPlaylist)(params["name"],params["chid"])
                elif params['vid'] :            threadit(Plugin(sysARG, sysInfo=params).playTV)(params["name"],params["chid"])
            elif params['isPlaylist']:          threadit(Plugin(sysARG, sysInfo=params).playPlaylist)(params["name"],params["chid"])
            elif params['vid']:                 threadit(Plugin(sysARG, sysInfo=params).playLive)(params["name"],params["chid"],params["vid"])
            else:                               threadit(Plugin(sysARG, sysInfo=params).playTV)(params["name"],params["chid"])
        elif params['vid']:
            if   mode == 'vod':                 threadit(Plugin(sysARG, sysInfo=params).playVOD)(params["title"],params["vid"])
            elif mode == 'dvr':                 threadit(Plugin(sysARG, sysInfo=params).playDVR)(params["title"],params["vid"])
            elif params['chid']:
                if   mode == 'broadcast':       threadit(Plugin(sysARG, sysInfo=params).playBroadcast)(params["name"],params["chid"],params["vid"])
                elif mode == 'radio':           threadit(Plugin(sysARG, sysInfo=params).playRadio)(params["name"],params["chid"],params["vid"])
        elif mode == 'resume' and params['chid']: 
                                                threadit(Plugin(sysARG, sysInfo=params).playPaused)(params["name"],params["chid"])
        elif mode == 'guide'                and SETTINGS.hasAddon(PVR_CLIENT_ID,install=True,enable=True): return SETTINGS.openGuide()
        elif mode == 'settings'             and SETTINGS.hasAddon(PVR_CLIENT_ID,install=True,enable=True): return SETTINGS.openSettings()
        else:                                   DIALOG.notificationDialog(LANGUAGE(32000))
        MONITOR().waitForAbort(float(SETTINGS.getSettingInt('RPC_Delay')/1000)) #delay to avoid thread crashes when fast channel changing ie PVR channel surfing.
        
if __name__ == '__main__':
    """
    Script entry point when run as main.

    Decodes plot information for current and next items, then initiates the main run
    function with the decoded items and system arguments.

    Side Effects:
        - Calls _run() to start PseudoTV Live's main logic.

    Returns:
        None
    """
    _run(sys.argv, decodePlot(BUILTIN.getInfoLabel('Plot')), decodePlot(BUILTIN.getInfoLabel('NextPlot')))