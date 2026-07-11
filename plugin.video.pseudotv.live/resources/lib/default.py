#   Copyright (C) 2026 Lunatixz
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
from variables  import *
from plugin     import Plugin

def _run(mode: str, sysInfo: dict = {}):
    LOG(f'Default: _run, mode = {mode}, sysInfo = {sysInfo}')
    Plugin(mode, sysInfo)
    
if __name__ == '__main__':
    try:
        try: 
            sysARG  = sys.argv
            sysInfo = dict(urllib.parse.parse_qsl(sysARG[2][1:].replace('.pvr','')))
        except Exception as e: 
            LOG('Default: sys.argv parse failed: %s' % e, xbmc.LOGDEBUG)
            sysARG  = ['plugin://plugin.video.pseudotv.live/', '1', sys.argv[1], 'resume:false']
            sysInfo = dict(urllib.parse.parse_qsl(sysARG[2][1:].replace('.pvr','')))
            
        if sysInfo.get('mode') is None:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
            if Globals.properties.getEXTProperty('%s.%s'%(ADDON_ID, 'has.Channels')) == "true":
                Globals._openGuide()
            else:
                Globals._openSettings()
                
        elif any(item in sysARG[2] for item in ['{catchup-id}', '{utc}', '{duration}', '{utcend}']):
            name = (Globals._unquoteString(sysInfo.get("name",'')) or Globals.builtin.getInfoLabel('ListItem.ChannelName') or ADDON_NAME)
            Globals.dialog.notificationDialog(LANGUAGE(32265)%(name))
            Globals.properties.setEXTProperty('%s.%s'%(ADDON_ID, 'chkPVRRefresh'),"true")
            xbmcplugin.setResolvedUrl(int(sysARG[1]), False, xbmcgui.ListItem())
            LOG(f'Default: __main__, failed! {sysARG[2]}', xbmc.LOGERROR)
            
        else:
            if hasattr(sys, 'listitem'):
                try:    fitem, nitem = Globals.listitems.buildDictListItem(sys.listitem), {}
                except Exception as e: 
                    LOG('Default: buildDictListItem failed: %s' % e, xbmc.LOGDEBUG)
                    fitem, nitem = Globals._decodePlot(Globals.builtin.getInfoLabel('ListItem.Plot')), Globals._decodePlot(Globals.builtin.getInfoLabel('ListItem.NextPlot'))
            else:
                fitem, nitem = Globals._decodePlot(Globals.builtin.getInfoLabel('ListItem.Plot')), Globals._decodePlot(Globals.builtin.getInfoLabel('ListItem.NextPlot'))
            chid, vid   = (sysInfo.get("chid")  or fitem.get('citem',{}).get('id')), FileAccess._decodeString(sysInfo.get("vid",""))
            name, title = (Globals._unquoteString(sysInfo.get("name",'')) or Globals.builtin.getInfoLabel('ListItem.ChannelName')), (Globals._unquoteString(sysInfo.get('title','')) or Globals.builtin.getInfoLabel('ListItem.label'))
            sysInfo.update({'mode':sysInfo.get('mode'),'sysARG':sysARG,'fitem':fitem,'nitem':nitem,'chid':chid,'vid':vid,'name':name,'title':title,'radio':sysInfo.get('mode') == "radio"})
            _run(sysInfo.get('mode'), sysInfo)
    except Exception as e: 
        LOG(f'Default: __main__, failed! {e}', xbmc.LOGERROR)
        Globals.dialog.notificationDialog(LANGUAGE(30079))
