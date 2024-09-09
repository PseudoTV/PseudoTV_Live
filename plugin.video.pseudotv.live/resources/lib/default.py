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

def run(sysARG):
    params = dict(urllib.parse.parse_qsl(sysARG[2][1:].replace('.pvr','')))
    log("Default: run, In params = %s"%(params))
    mode   = (params.get("mode")  or 'guide')
    chid   = (params.get("chid")  or -1)
    
    params['radio']      = (params.get("radio") or 'False').lower() == "true"
    params['chnumlabel'] = BUILTIN.getInfoLabel('ChannelNumberLabel')
    params['name']       = (unquoteString(params.get("name",''))  or BUILTIN.getInfoLabel('ChannelName'))
    params['title']      = (unquoteString(params.get("title",'')) or BUILTIN.getInfoLabel('label'))
    params['duration']   = int((params.get('duration')            or timeString2Seconds(BUILTIN.getInfoLabel('Duration(hh:mm:ss)')) or '0'))
    params['vid']        = (decodeString(params.get("vid",'')     or None))
    params['chpath']     = BUILTIN.getInfoLabel('FileNameAndPath')
    params['citem']      = {'id':chid}
    params['fitem']      = decodePlot(BUILTIN.getInfoLabel('Plot'))
    params['nitem']      = decodePlot(BUILTIN.getInfoLabel('NextPlot'))
    params['playcount']  = 0
    params['isLinear']   = True if mode == 'live' else False
    params['isPlaylist'] = bool(SETTINGS.getSettingInt('Playback_Method'))
    params['progress']   = (BUILTIN.getInfoLabel('Progress'),BUILTIN.getInfoLabel('PercentPlayed'))
    params['now']        = (params.get('now') or int(getUTCstamp()))
    log("Default: run, Out params = %s"%(params))

    if mode == 'guide':
        hasAddon(PVR_CLIENT_ID,install=True,enable=True)
        BUILTIN.executebuiltin("Dialog.Close(all)") 
        BUILTIN.executebuiltin("ReplaceWindow(TVGuide,pvr://channels/tv/%s)"%(quoteString(ADDON_NAME)))
    elif mode == 'settings' and hasAddon(PVR_CLIENT_ID,install=True,enable=True): SETTINGS.openSettings()
    elif chid == -1:             return DIALOG.notificationDialog(LANGUAGE(32000))
    elif mode in ['vod','dvr']:  threadit(Plugin(sysARG, sysInfo=params).playVOD)(params.get('title'),params.get('vid'))
    elif mode == 'live':
        if   params['isPlaylist']: threadit(Plugin(sysARG, sysInfo=params).playPlaylist)(params.get('name'),chid)
        elif params['vid'] :       threadit(Plugin(sysARG, sysInfo=params).playLive)(params.get('name'),chid,params.get('vid'))
        else:                      threadit(Plugin(sysARG, sysInfo=params).playTV)(params.get('name'),chid)
    elif mode == 'broadcast':    threadit(Plugin(sysARG, sysInfo=params).playBroadcast)(params.get('name'),chid,params.get('vid'))
    elif mode == 'radio':        threadit(Plugin(sysARG, sysInfo=params).playRadio)(params.get('name'),chid,params.get('vid'))

    # elif not isPlaylist and chid and not vid: return DIALOG.notificationDialog(LANGUAGE(32166)%(PVR_CLIENT_NAME,SETTINGS.IPTV_SIMPLE_SETTINGS().get('m3uRefreshIntervalMins')))
if __name__ == '__main__': run(sys.argv)