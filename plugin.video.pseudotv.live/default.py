#   Copyright (C) 2021 Lunatixz
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

# -entry point-
from resources.lib.globals   import *
from resources.lib.plugin    import Plugin

class Default:
    def __init__(self, sysARG=sys.argv, service=None):
        self.sysARG = sysARG
        self.plugin = Plugin(sysARG=self.sysARG)
                
                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getParams(self):
        return dict(urllib.parse.parse_qsl(self.sysARG[2][1:]))


    def run(self):  
        params  = self.getParams()
        name    = (unquote(params.get("name",'')) or None)
        channel = (params.get("channel",'')       or None)
        url     = (params.get("url",'')           or None)
        id      = (params.get("id",'')            or None)
        mode    = (params.get("mode",'')          or None)
        radio   = (params.get("radio",'')         or 'False') == "True"
        self.log("Name = %s, Channel = %s, URL = %s, ID = %s, Radio = %s, Mode = %s"%(name,channel,url,id,radio,mode))

        if mode is None:
            if isBusy(): Dialog().notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            else:        SETTINGS.openSettings()
            xbmc.executebuiltin("Action(Close)") #todo debug busy dialog
        elif mode == 'vod':  self.plugin.playVOD(name, id)
        elif mode == 'play':
            if radio: self.plugin.playRadio(name, id)
            else:     self.plugin.playChannel(name, id, isPlaylist=bool(SETTINGS.getSettingInt('Playback_Method')))
       
if __name__ == '__main__': Default(sys.argv).run()