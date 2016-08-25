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

import datetime, socket, json, copy, re, requests

from utils import *
from Globals import *


class Upnp:

    def __init__(self):   
        self.IPPlst, self.AUTHlst = self.initUPNP() # collect upnp mirror ips/pw

        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Upnp: ' + msg, level)
        
        
    def initUPNP(self):
        IPPlst = []
        PWlst = []
        #UPNP Clients
        if REAL_SETTINGS.getSetting("UPNP1") == "true":
            IPPlst.append(REAL_SETTINGS.getSetting("UPNP1_IPP"))
            PWlst.append(REAL_SETTINGS.getSetting("UPNP1_UPW"))
        if REAL_SETTINGS.getSetting("UPNP2") == "true":
            IPPlst.append(REAL_SETTINGS.getSetting("UPNP2_IPP"))
            PWlst.append(REAL_SETTINGS.getSetting("UPNP2_UPW"))
        if REAL_SETTINGS.getSetting("UPNP3") == "true":
            IPPlst.append(REAL_SETTINGS.getSetting("UPNP3_IPP"))
            PWlst.append(REAL_SETTINGS.getSetting("UPNP3_UPW"))
        self.log("initUPNP = " + str(IPPlst))
        return IPPlst, PWlst

        
    def RequestExtJson(self, IPP, AUTH, params):
        self.log('RequestExtJson, IPP = ' + IPP)
        try:
            xbmc_host, xbmc_port = IPP.split(":")
            user, password = AUTH.split(":")
            kodi_url = 'http://' + xbmc_host +  ':' + xbmc_port + '/jsonrpc'
            headers = {'Content-Type': 'application/json'}
            r = requests.post(
                    kodi_url,
                    data=json.dumps(params),
                    headers=headers,
                    auth=(user,password)) 
            return r.json()
        except Exception,e:
            self.log('RequestExtJson, failed! ' + str(e), xbmc.LOGERROR)
            
            
    def SendExtJson(self, IPP, params):
        self.log('SendExtJson, IPP = ' + IPP)
        try:
            xbmc_host, xbmc_port = IPP.split(":")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((xbmc_host, 9090))
            params2 = copy.copy(params)
            params2["jsonrpc"] = "2.0"
            params2["id"] = 1
            s.send(json.dumps(params2))
            s.shutdown(socket.SHUT_RDWR)
            s.close()
        except Exception,e:
            self.log('SendExtJson, failed! ' + str(e), xbmc.LOGERROR)


    def isPlayingUPNP(self, IPP, AUTH, label, file):
        self.log('isPlayingUPNP, IPP = ' + IPP)
        params = ({"jsonrpc":"2.0","id":1,"method":"Player.GetItem","params":{"playerid":1,"properties":["file"]}})
        try:
            json_detail = self.RequestExtJson(IPP, AUTH, params)
            playing_label = json_detail['result']['item']['label']
        except:
            return False
        try:
            playing_file = json_detail['result']['item']['file']
        except:
            playing_file = ''
        
        self.log('isPlayingUPNP, ' + playing_label.lower() + ' ?=? ' + playing_label.lower())
        self.log('isPlayingUPNP, ' + file + ' ?=? ' + playing_file)
        if playing_label.lower() == playing_label.lower():
            return True
        elif file == playing_file:
            return True
        else:
            return False
            
         
    def chkUPNP(self, label, file, seektime): 
        self.log('chkUPNP') 
        for i in range(len(self.IPPlst)):   
            if self.isPlayingUPNP(self.IPPlst[i], self.AUTHlst[i], label, file) == False:
                self.log('chkUPNP, ' + str(self.IPPlst[i]) + ' not playing') 
                if seektime > 0:
                    seek = str(datetime.timedelta(seconds=seektime))
                    self.log('chkUPNP, seek = ' + seek)
                    seek = seek.split(":")
                    try:
                        hours = int(seek[0])
                    except:
                        hours = 0
                    try:
                        minutes = int(seek[1])
                    except:
                        minutes = 0

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
                self.SendExtJson(self.IPPlst[i],params)
            
            
    def SendUPNP(self, label, file, seektime):
        self.log('SendUPNP')
        for i in range(len(self.IPPlst)):  
            if seektime > 0:
                seek = str(datetime.timedelta(seconds=seektime))
                self.log('SendUPNP, seek = ' + seek)
                seek = seek.split(":")
                try:
                    hours = int(seek[0])
                except:
                    hours = 0
                try:
                    minutes = int(seek[1])
                except:
                    minutes = 0

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
            self.SendExtJson(self.IPPlst[i],params)

            
    def StopUPNP(self):
        self.log('StopUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Player.Stop","params":{"playerid":1}})       
        for i in range(len(self.IPPlst)):  
            self.SendExtJson(self.IPPlst[i],params)
        
        
    def PauseUPNP(self):
        self.log('PauseUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"pause"}})
        for i in range(len(self.IPPlst)):  
            self.SendExtJson(self.IPPlst[i],params)
        
        
    def ResumeUPNP(self):
        self.log('ResumeUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"play"}})       
        for i in range(len(self.IPPlst)):  
            self.SendExtJson(self.IPPlst[i],params)
        
        
    def RWUPNP(self):
        self.log('RWUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"stepback"}})          
        for i in range(len(self.IPPlst)):  
            self.SendExtJson(self.IPPlst[i],params)
        
        
    def FFUPNP(self):
        self.log('FFUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"stepforward"}})
        for i in range(len(self.IPPlst)):  
            self.SendExtJson(self.IPPlst[i],params)
        
        
    def PlaylistUPNP(self, IPP, file):
        self.log('PlaylistUPNP')
        params = ({"jsonrpc":"2.0","id":1,"method":"Player.Open","params":{"item": {"file": file}}})
        for i in range(len(self.IPPlst)):  
            self.SendExtJson(self.IPPlst[i],params)
