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
from globals    import *
from m3u        import M3U
from xmltvs     import XMLTVS

class Record:
    def __init__(self, sysARG: dict={}, listitem: xbmcgui.ListItem=xbmcgui.ListItem(), fitem: dict={}):
        log('Record: __init__, sysARG = %s, fitem = %s\npath = %s'%(sysARG,fitem,listitem.getPath()))
        self.sysARG   = sysARG
        self.fitem    = fitem
        self.listitem = listitem
        
        
    def add(self):
        self.fitem['label'] = (self.fitem.get('label') or self.listitem.getLabel())
        m3u   = M3U()
        xmltv = XMLTVS()
        ritem = m3u.getRecordItem(self.fitem)
        if DIALOG.yesnoDialog('Would you like to add:\n[B]%s[/B]\nto recordings?'%(ritem['label'])):
            with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
                if (m3u.addRecording(ritem), xmltv.addRecording(ritem,self.fitem)):
                    DIALOG.notificationWait('%s\n%s'%(ritem['label'],LANGUAGE(30116)))
        del m3u
        del xmltv
    
            
    def remove(self):
        self.fitem['label'] = (self.fitem.get('label') or self.listitem.getLabel())
        m3u   = M3U()
        xmltv = XMLTVS()
        ritem = m3u.getRecordItem(self.fitem)
        if DIALOG.yesnoDialog('Would you like to remove:\n[B]%s[/B]\nfrom recordings?'%(ritem['label'])):
            with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
                if (m3u.delRecording(ritem), xmltv.delRecording(ritem)):
                    DIALOG.notificationWait('%s\n%s'%(ritem['label'],LANGUAGE(30118)))
        del m3u
        del xmltv
            
            
if __name__ == '__main__': 
    try:    param = sys.argv[1]
    except: param = None
    log('Record: __main__, param = %s'%(param))
    if   param == 'add': Record(sys.argv,listitem=sys.listitem,fitem=decodePlot(BUILTIN.getInfoLabel('Plot'))).add()
    elif param == 'del': Record(sys.argv,listitem=sys.listitem,fitem=decodePlot(BUILTIN.getInfoLabel('Plot'))).remove()
    