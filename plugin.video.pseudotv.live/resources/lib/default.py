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
    """
    Main entry point for PseudoTV Live's functionality.

    This function handles various modes of playback and interaction based on the parameters passed.
    These modes include live TV, video-on-demand (VOD), DVR playback, guide display, and more.
    It also processes system arguments and settings to determine the appropriate behavior.

    Args:
        sysARG (list): System arguments passed by the Kodi interface.
        fitem (dict, optional): Dictionary containing information about the current (featured) item. Defaults to an empty dictionary.
        nitem (dict, optional): Dictionary containing information about the next item. Defaults to an empty dictionary.

    Behavior:
        - Parses system arguments and determines the mode of operation.
        - Depending on the mode, it invokes the appropriate plugin functionality (e.g., play live TV, VOD, DVR, etc.).
        - Utilizes utility functions like `threadit` for threading and `PROPERTIES` for managing app states.

    Supported Modes:
        - 'live': Plays live TV or a playlist based on the provided parameters.
        - 'vod': Plays video-on-demand content.
        - 'dvr': Plays DVR recordings.
        - 'resume': Resumes paused playback.
        - 'broadcast': Simulates broadcast playback.
        - 'radio': Plays radio streams.
        - 'guide': Opens the TV guide using the PVR client.
        - 'settings': Opens the settings menu.

    Notifications:
        - Displays notification dialogs for unsupported modes or errors.

    """
    with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
        params = dict(urllib.parse.parse_qsl(sysARG[2][1:].replace('.pvr','')))
        mode = (params.get("mode")  or 'guide')
        params['fitem']      = fitem
        params['nitem']      = nitem
        params['vid']        = decodeString(params.get("vid",''))
        params["chid"]       = (params.get("chid")  or fitem.get('citem',{}).get('id'))
        params['title']      = (params.get('title') or BUILTIN.getInfoLabel('label'))
        params['name']       = (unquoteString(params.get("name",'')) or BUILTIN.getInfoLabel('ChannelName'))
        params['isPlaylist'] = bool(SETTINGS.getSettingInt('Playback_Method'))
        log("Default: run, params = %s"%(params))
        
        if   PROPERTIES.isRunning('togglePVR'): DIALOG.notificationDialog(LANGUAGE(32166))
        elif mode == 'live':
            if params.get('start') == '{utc}':
                PROPERTIES.setPropTimer('chkPVRRefresh')
                params.update({'start':0,'stop':0,'duration':0})
                if   params['isPlaylist']:      threadit(Plugin(sysARG, sysInfo=params).playPlaylist)(params["name"],params["chid"])
                elif params['vid'] :            threadit(Plugin(sysARG, sysInfo=params).playTV)(params["name"],params["chid"])
            elif params['isPlaylist']:          threadit(Plugin(sysARG, sysInfo=params).playPlaylist)(params["name"],params["chid"])
            elif params['vid'] :                threadit(Plugin(sysARG, sysInfo=params).playLive)(params["name"],params["chid"],params["vid"])
            else:                               threadit(Plugin(sysARG, sysInfo=params).playTV)(params["name"],params["chid"])
        elif mode == 'vod':                     threadit(Plugin(sysARG, sysInfo=params).playVOD)(params["title"],params["vid"])
        elif mode == 'dvr':                     threadit(Plugin(sysARG, sysInfo=params).playDVR)(params["title"],params["vid"])
        elif mode == 'resume':                  threadit(Plugin(sysARG, sysInfo=params).playPaused)(params["name"],params["chid"])
        elif mode == 'broadcast':               threadit(Plugin(sysARG, sysInfo=params).playBroadcast)(params["name"],params["chid"],params["vid"])
        elif mode == 'radio':                   threadit(Plugin(sysARG, sysInfo=params).playRadio)(params["name"],params["chid"],params["vid"])
        elif mode == 'guide'                and hasAddon(PVR_CLIENT_ID,install=True,enable=True): SETTINGS.openGuide()
        elif mode == 'settings'             and hasAddon(PVR_CLIENT_ID,install=True,enable=True): SETTINGS.openSettings()
        else:                                   DIALOG.notificationDialog(LANGUAGE(32000))
        MONITOR().waitForAbort(float(SETTINGS.getSettingInt('RPC_Delay')/1000)) #delay to avoid thread crashes when fast channel changing.
        
if __name__ == '__main__':
    """
    Runs the script when executed as the main module.

    It decodes information about the current and next items using the `decodePlot` function
    and then invokes the `run` function with the appropriate arguments.
    """
    run(sys.argv, fitem=decodePlot(BUILTIN.getInfoLabel('Plot')), nitem=decodePlot(BUILTIN.getInfoLabel('NextPlot')))