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
    params  = dict(urllib.parse.parse_qsl(sysARG[2][1:].replace('.pvr','')))
    name    = (unquoteString(params.get("name",'')) or None)
    channel = (params.get("channel",'')             or None)
    url     = (params.get("url",'')                 or None)
    id      = (params.get("id",'')                  or None)
    mode    = (params.get("mode",'')                or 'guide')
    radio   = (params.get("radio",'')               or 'False').lower() == "true"
    log("Default: run, params = %s"%(params))

    if DEBUG_ENABLED:
        if BUILTIN.getInfoBool('HasAddon(%s)'%(PVR_CLIENT),'System'):
            if not BUILTIN.getInfoBool('AddonIsEnabled(%s)'%(PVR_CLIENT),'System'):
                BUILTIN.executebuiltin('"EnableAddon(%s)'%(PVR_CLIENT))
        else:
            BUILTIN.executebuiltin('"InstallAddon(%s)'%(PVR_CLIENT))
        
    if mode == 'guide':
        BUILTIN.executebuiltin("Dialog.Close(all)") 
        BUILTIN.executebuiltin("ActivateWindow(TVGuide,%s)"%(quoteString(SETTINGS.getCacheSetting('pseudopvr', default='pvr://channels/tv/'))))
    elif mode == 'settings': 
        BUILTIN.executebuiltin('Addon.OpenSettings(%s)'%ADDON_ID)
    elif mode == 'vod': 
        timerit(Plugin(sysARG).playVOD)(.001,(name,id))
    elif mode == 'play':
        if radio: threadit(Plugin(sysARG).playRadio)(name,id)
        else:     threadit(Plugin(sysARG).playChannel)(name,id,bool(SETTINGS.getSettingInt('Playback_Method')))

if __name__ == '__main__': run(sys.argv)