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

from globals   import *
from plugin    import Plugin

def run(sysARG):
    params    = dict(urllib.parse.parse_qsl(sysARG[2][1:].replace('.pvr','')))
    name      = (unquoteString(params.get("name",'')) or None)
    channel   = (params.get("channel",'')             or None)
    url       = (params.get("url",'')                 or None)
    id        = (params.get("id",'')                  or None)
    endtime   = (params.get("endtime",'')             or None)
    mode      = (params.get("mode",'')                or 'guide')
    radio     = (params.get("radio",'')               or 'False').lower() == "true"
    log("Default: run, params = %s"%(params))
    
    if mode == 'guide':
        hasAddon(PVR_CLIENT,install=True,enable=True)
        BUILTIN.executebuiltin("Dialog.Close(all)") 
        BUILTIN.executebuiltin("ReplaceWindow(TVGuide,pvr://channels/tv/%s)"%(ADDON_NAME))
    elif mode == 'settings': 
        hasAddon(PVR_CLIENT,install=True,enable=True)
        BUILTIN.executebuiltin('Addon.OpenSettings(%s)'%ADDON_ID)
    elif mode == 'vod': 
        threadit(Plugin(sysARG).playVOD)(name,id)
    elif mode == 'broadcast': 
        threadit(Plugin(sysARG).playBroadcast)(name,channel,datetime.datetime.fromtimestamp((datetime.datetime.timestamp(strpTime(endtime, DTJSONFORMAT)) - getTimeoffset())).strftime(DTJSONFORMAT))
    elif mode == 'play':
        if radio: threadit(Plugin(sysARG).playRadio)(name,channel)
        else:     threadit(Plugin(sysARG).playChannel)(name,channel,bool(SETTINGS.getSettingInt('Playback_Method')))

if __name__ == '__main__': run(sys.argv)



