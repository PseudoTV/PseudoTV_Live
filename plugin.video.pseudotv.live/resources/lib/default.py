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
    params['playlist'] = bool(SETTINGS.getSettingInt('Playback_Method'))
    
    name      = (unquoteString(params.get("name",''))  or None)
    title     = (unquoteString(params.get("title",'')) or None)
    chid      = (params.get("chid",'')                 or None)
    url       = (params.get("url",'')                  or None)
    vid       = decodeString(params.get("vid",'')      or None)
    start     = (params.get("start",'')                or None)
    duration  = (params.get("duration",'')             or None)
    mode      = (params.get("mode",'')                 or 'guide')
    radio     = (params.get("radio",'')                or 'False').lower() == "true"
    log("Default: run, params = %s"%(params))
    
    if mode == 'guide':
        hasAddon(PVR_CLIENT_ID,install=True,enable=True)
        BUILTIN.executebuiltin("Dialog.Close(all)") 
        BUILTIN.executebuiltin("ReplaceWindow(TVGuide,pvr://channels/tv/%s)"%(quoteString(ADDON_NAME)))
    elif mode == 'settings': 
        hasAddon(PVR_CLIENT_ID,install=True,enable=True)
        BUILTIN.executebuiltin('Addon.OpenSettings(%s)'%ADDON_ID)
    elif mode == 'vod': 
        threadit(Plugin(sysARG).playVOD)(title,vid)
    elif mode == 'live':
        if params['playlist']:
            threadit(Plugin(sysARG).playPlaylist)(name,chid)
        else:
            threadit(Plugin(sysARG).playLive)(name,chid,vid)
    elif mode == 'broadcast': 
        threadit(Plugin(sysARG).playBroadcast)(name,chid,vid)
    elif mode == 'radio':
        threadit(Plugin(sysARG).playRadio)(name,chid,vid)
    elif mode == 'tv':
        threadit(Plugin(sysARG).playTV)(name,chid)

if __name__ == '__main__': run(sys.argv)



