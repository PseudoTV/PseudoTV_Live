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
        self.sysARG          = sysARG
        self.fitem           = fitem
        self.listitem        = listitem
        self.fitem['label']  = (fitem.get('label') or listitem.getLabel())
        
        
    def add(self):
        if not PROPERTIES.isRunning('Record.add'):
            with PROPERTIES.setRunning('Record.add'):
                now   = timeString2Seconds(BUILTIN.getInfoLabel('Time(hh:mm:ss)','System'))
                start = timeString2Seconds(BUILTIN.getInfoLabel('StartTime').split(' ')[0] +':00')
                stop  = timeString2Seconds(BUILTIN.getInfoLabel('EndTime').split(' ')[0] +':00')
                if (now > start and now < stop):
                    opt  ='Incl. Resume'
                    seek = (now - start) - SETTINGS.getSettingInt('OSD_Timer') #add rollback buffer
                    msg  = '%s or %s'%(LANGUAGE(30119),LANGUAGE(30152))
                else:
                    opt  = ''
                    seek = 0
                    msg  = LANGUAGE(30119)
                retval = DIALOG.yesnoDialog('Would you like to add:\n[B]%s[/B]\nto %s recordings?'%(self.fitem['label'],msg),customlabel=opt)
                if retval or int(retval) > 0:
                    with PROPERTIES.interruptActivity(), BUILTIN.busy_dialog():
                        m3u   = M3U()
                        ritem = m3u.getRecordItem(self.fitem,{'1':0,'2':seek}[str(int(retval))])
                        if (m3u.addRecording(ritem), XMLTVS().addRecording(ritem,self.fitem)):
                            DIALOG.notificationWait('%s\n%s'%(ritem['label'],LANGUAGE(30116)))
                            PROPERTIES.setEpochTimer('chkPVRRefresh')
                        del m3u
        else: DIALOG.notificationDialog(LANGUAGE(32000))
        
 
    def remove(self):
        if not PROPERTIES.isRunning('Record.remove'):
            with PROPERTIES.setRunning('Record.remove'):
                if DIALOG.yesnoDialog('Would you like to remove:\n[B]%s[/B]\nfrom recordings?'%(self.fitem['label'])):
                    with PROPERTIES.interruptActivity(), BUILTIN.busy_dialog():
                        ritem = (self.fitem.get('citem') or {"name":self.fitem['label'],"path":self.listitem.getPath()})
                        log('Record: remove, ritem = %s'%(ritem))
                        if (M3U().delRecording(ritem), XMLTVS().delRecording(ritem)):
                            DIALOG.notificationWait('%s\n%s'%(ritem['name'],LANGUAGE(30118)))
                            PROPERTIES.setEpochTimer('chkPVRRefresh')
        else: DIALOG.notificationDialog(LANGUAGE(32000))
                
            
if __name__ == '__main__': 
    try:    param = sys.argv[1]
    except: param = None
    log('Record: __main__, param = %s'%(param))
    if   param == 'add': Record(sys.argv,listitem=sys.listitem,fitem=decodePlot(BUILTIN.getInfoLabel('Plot'))).add()
    elif param == 'del': Record(sys.argv,listitem=sys.listitem,fitem=decodePlot(BUILTIN.getInfoLabel('Plot'))).remove()
    