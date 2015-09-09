#   Copyright (C) 2015 Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import datetime, socket, json, copy

from Globals import *

socket.setdefaulttimeout(30)
    
class Upnp:


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Upnp: ' + msg, level)

    
    def logDebug(self, msg, level = xbmc.LOGDEBUG):
        if DEBUG == 'true':
            log('Upnp: ' + msg, level)
            
            
    def SendExtJson(self, IPP, params):
        self.log('SendExtJson')
        try:
            xbmc_host = str(IPP.split(":")[0])
            xbmc_port = int(IPP.split(":")[1])
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((xbmc_host, xbmc_port))
            params2 = copy.copy(params)
            params2["jsonrpc"] = "2.0"
            params2["id"] = 1
            s.send(json.dumps(params2))
            s.shutdown(socket.SHUT_RDWR)
            s.close()
        except:
            if NOTIFY == True:
                xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", xbmc_host + " Failed to respond.", 1000, THUMB) )
        
        
    def SendUPNP(self, IPP, file, seektime):
        self.log('SendUPNP')
        if seektime > 0:
            seek = str(datetime.timedelta(seconds=seektime))
            seek = seek.split(":")
            hours = int(seek[0])
            minutes = int(seek[1])
            Mseconds = str(seek[2])
            seconds = int(Mseconds.split(".")[0])
            
            try:
                milliseconds = int(Mseconds.split(".")[1])
                milliseconds = int(str(milliseconds)[:3])
            except:
                milliseconds = 0
                
            millisecondOFFSET = float(REAL_SETTINGS.getSetting("UPNP_OFFSET"))
            milliseconds + millisecondOFFSET
            params = ({"jsonrpc": "2.0", "method": "Player.Open", "params": {"item": {"file": file},"options":{"resume":{"hours":hours,"minutes":minutes,"seconds":seconds,"milliseconds":milliseconds}}}})
        else:
            params = ({"jsonrpc": "2.0", "method": "Player.Open", "params": {"item": {"path": file}}})
        self.SendExtJson(IPP, params)

        
    def StopUPNP(self, IPP):
        self.log('StopUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Player.Stop","params":{"playerid":1}})
        self.SendExtJson(IPP,params)
        
        
    def PauseUPNP(self, IPP):
        self.log('PauseUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"pause"}})
        self.SendExtJson(IPP,params)
        
        
    def ResumeUPNP(self, IPP):
        self.log('ResumeUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"play"}})       
        self.SendExtJson(IPP,params)
        
        
    def RWUPNP(self, IPP):
        self.log('RWUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"stepback"}})          
        self.SendExtJson(IPP,params)
        
        
    def FFUPNP(self, IPP):
        self.log('FFUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"stepforward"}})
        self.SendExtJson(IPP,params)
        
        
    def PlaylistUPNP(self, IPP, file):
        self.log('PlaylistUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Player.Open","params":{"item": {"file": file}}})
        self.SendExtJson(IPP,params)