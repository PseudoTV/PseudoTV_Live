#   Copyright (C) 2015 Lunatixz, t0mm0, jwdempsey, esxbr, yrabl
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

import sys, os, re, datetime, time
import urllib2, traceback, socket
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

from xml.dom import minidom
from xml.etree import ElementTree as ET
from resources.lib.Globals import *
from resources.lib.utils import *
from resources.lib.FileAccess import FileAccess
try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
    
socket.setdefaulttimeout(15)   

try:
    class ustvnow:
        def __init__(self):
            self.log('__init__')
            self.mBASE_URL = 'http://m-api.ustvnow.com'
            self.uBASE_URL = 'http://lv2.ustvnow.com'
            self.channels = ['ABC','CBS','CW','FOX','NBC','PBS','My9','A&E','AMC','Animal Planet','Bravo','Cartoon Network','CNBC','CNN','Comedy Central','Discovery','ESPN','Fox News','FX','History','Lifetime','National Geographic','Nickelodeon','SPIKE TV','Syfy','TBS','TNT','USA']

            
        def log(self, msg, level = xbmc.LOGDEBUG):
            log('USTVnow: ' + msg, level)

            
        def _fetch(self, url, form_data=False):
            self.log('_fetch url = ' + url)
            opener = urllib2.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            req = urllib2.Request(url)
            try:
                response = urllib2.urlopen(req)
                return response
            except urllib2.URLError, e:
                return False


        def _get_json(self, path):
            self.log('_get_json')
            try:
                result = guide.cacheFunction(self._get_json_NEW, path)
                if len(result) == 0:
                    raise Exception()
            except:
                result = self._get_json_NEW(path)
            if not result:
                result = False
            return result

            
        def _get_json_NEW(self, path):
            self.log('_get_json_NEW')
            content = False
            response = self._fetch('%s/%s' % (self.mBASE_URL, path))
            if response:
                content = json.loads(response.read())
            return content

            
        def get_guidedata(self):
            self.log('get_guidedata')
            cnt = 0
            content = self._get_json('gtv/1/live/channelguide')
            if content == False:
                return ''
                
            results = content['results'];
            now = time.time();
            doc = minidom.Document();
            base = doc.createElement('tv');
            base.setAttribute("cache-version", str(now));
            base.setAttribute("cache-time", str(now));
            base.setAttribute("generator-info-name", "USTVnow Guidedata");
            base.setAttribute("generator-info-url", "http://www.xmltv.org/");
            doc.appendChild(base)
            channels = [{'sname': u'WHTM'   , 'name': u'ABC',                         'icon': u'http://m.ustvnow.com/images/WHTM.png'}, 
                        {'sname': u'WHP'    , 'name': u'CBS',                         'icon': u'http://m.ustvnow.com/images/WHP.png'}, 
                        {'sname': u'WLYH'   , 'name': u'CW',                          'icon': u'http://m.ustvnow.com/images/WLYH.png'}, 
                        {'sname': u'WPMT'   , 'name': u'FOX',                         'icon': u'http://m.ustvnow.com/images/WPMT.png'}, 
                        {'sname': u'WGAL'   , 'name': u'NBC',                         'icon': u'http://m.ustvnow.com/images/WGAL.png'}, 
                        {'sname': u'WPSU'   , 'name': u'PBS',                         'icon': u'http://m.ustvnow.com/images/WPSU.png'}, 
                        {'sname': u'WHVLLD' , 'name': u'My9',                         'icon': u'http://m.ustvnow.com/images/WHVLLD.png'}, 
                        {'sname': u'AETV'   , 'name': u'AETV',                        'icon': u'http://m.ustvnow.com/images/AETV.png'}, 
                        {'sname': u'AMC'    , 'name': u'AMC',                         'icon': u'http://m.ustvnow.com/images/AMC.png'}, 
                        {'sname': u'APL'    , 'name': u'Animal Planet',               'icon': u'http://m.ustvnow.com/images/APL.png'}, 
                        {'sname': u'BRAVO'  , 'name': u'Bravo',                       'icon': u'http://m.ustvnow.com/images/BRAVO.png'}, 
                        {'sname': u'TOON'   , 'name': u'Cartoon Network',             'icon': u'http://m.ustvnow.com/images/TOON.png'}, 
                        {'sname': u'CNBC'   , 'name': u'CNBC',                        'icon': u'http://m.ustvnow.com/images/CNBC.png'}, 
                        {'sname': u'CNN'    , 'name': u'CNN',                         'icon': u'http://m.ustvnow.com/images/CNN.png'}, 
                        {'sname': u'COMEDY' , 'name': u'Comedy Central',              'icon': u'http://m.ustvnow.com/images/COMEDY.png'}, 
                        {'sname': u'DSC'    , 'name': u'Discovery Channel',           'icon': u'http://m.ustvnow.com/images/DSC.png'}, 
                        {'sname': u'ESPN'   , 'name': u'ESPN',                        'icon': u'http://m.ustvnow.com/images/ESPN.png'}, 
                        {'sname': u'FNC'    , 'name': u'Fox News Channel',            'icon': u'http://m.ustvnow.com/images/FNC.png'}, 
                        {'sname': u'FX'     , 'name': u'FX',                          'icon': u'http://m.ustvnow.com/images/FX.png'}, 
                        {'sname': u'HISTORY', 'name': u'History',                     'icon': u'http://m.ustvnow.com/images/HISTORY.png'}, 
                        {'sname': u'LIFE'   , 'name': u'Lifetime',                    'icon': u'http://m.ustvnow.com/images/LIFE.png'}, 
                        {'sname': u'NGC'    , 'name': u'National Geographic Channel', 'icon': u'http://m.ustvnow.com/images/NGC.png'}, 
                        {'sname': u'NIK'    , 'name': u'Nickelodeon',                 'icon': u'http://m.ustvnow.com/images/NIK.png'}, 
                        {'sname': u'SPIKETV', 'name': u'SPIKE TV',                    'icon': u'http://m.ustvnow.com/images/SPIKETV.png'}, 
                        {'sname': u'SYFY'   , 'name': u'Syfy',                        'icon': u'http://m.ustvnow.com/images/SYFY.png'}, 
                        {'sname': u'TBS'    , 'name': u'TBS',                         'icon': u'http://m.ustvnow.com/images/TBS.png'}, 
                        {'sname': u'TNT'    , 'name': u'TNT',                         'icon': u'http://m.ustvnow.com/images/TNT.png'}, 
                        {'sname': u'USA'    , 'name': u'USA',                         'icon': u'http://m.ustvnow.com/images/USA.png'}]
            
            for channel in channels:
                cnt +=1
                name = channel['name'];
                id = channel['sname'];
                c_entry = doc.createElement('channel');
                c_entry.setAttribute("id", id);
                base.appendChild(c_entry)
                dn_entry = doc.createElement('display-name');
                dn_entry_content = doc.createTextNode(self.cleanChanName(name));
                dn_entry.appendChild(dn_entry_content);
                c_entry.appendChild(dn_entry);
                dn_entry = doc.createElement('display-name');
                dn_entry_content = doc.createTextNode(self.cleanChanName(id));
                dn_entry.appendChild(dn_entry_content);
                c_entry.appendChild(dn_entry);
                icon_entry = doc.createElement('icon');
                icon_entry.setAttribute("src", channel['icon']);
                c_entry.appendChild(icon_entry);

            for programme in results:
                start_time  = datetime.datetime.fromtimestamp(float(programme['ut_start']));
                stop_time   = start_time + datetime.timedelta(seconds=int(programme['guideremainingtime']));

                pg_entry = doc.createElement('programme');
                pg_entry.setAttribute("start", start_time.strftime('%Y%m%d%H%M%S 0'));
                pg_entry.setAttribute("stop", stop_time.strftime('%Y%m%d%H%M%S 0'));
                pg_entry.setAttribute("channel", programme['callsign']);
                base.appendChild(pg_entry);

                t_entry = doc.createElement('title');
                t_entry.setAttribute("lang", "en");
                t_entry_content = doc.createTextNode(programme['title']);
                t_entry.appendChild(t_entry_content);
                pg_entry.appendChild(t_entry);

                st_entry = doc.createElement('sub-title');
                st_entry.setAttribute("lang", "en");
                st_entry_content = doc.createTextNode(programme['episode_title']);
                st_entry.appendChild(st_entry_content);
                pg_entry.appendChild(st_entry);

                d_entry = doc.createElement('desc');
                d_entry.setAttribute("lang", "en");
                d_entry_content = doc.createTextNode(programme['description']);
                d_entry.appendChild(d_entry_content);
                pg_entry.appendChild(d_entry);

                dt_entry = doc.createElement('date');
                dt_entry_content = doc.createTextNode(start_time.strftime('%Y%m%d'));
                dt_entry.appendChild(dt_entry_content);
                pg_entry.appendChild(dt_entry);

                c_entry = doc.createElement('category');
                c_entry_content = doc.createTextNode(programme['xcdrappname']);
                c_entry.appendChild(c_entry_content);
                pg_entry.appendChild(c_entry);
                d_entry = doc.createElement('length');
                d_entry.setAttribute("units", "seconds");
                d_entry_content = doc.createTextNode(str(programme['actualremainingtime']));
                d_entry.appendChild(d_entry_content);
                pg_entry.appendChild(d_entry);
                en_entry = doc.createElement('episode-num');
                en_entry.setAttribute('system', 'dd_progid');
                en_entry_content = doc.createTextNode(programme['content_id']);
                en_entry.appendChild(en_entry_content);
                pg_entry.appendChild(en_entry);

                i_entry = doc.createElement('icon');
                i_entry.setAttribute("src", 'http://mc.ustvnow.com/gtv/1/live/viewposter?srsid=' + str(programme['srsid']) + '&cs=' + programme['callsign'] + '&tid=' + programme['mediatype']);
                pg_entry.appendChild(i_entry);
            return uni(doc)


        def cleanChanName(self, string):
            string = string.strip()
            string = string.replace('WLYH','CW').replace('WHTM','ABC').replace('WPMT','FOX').replace('WPSU','PBS').replace('WHP','CBS').replace('WGAL','NBC').replace('WHVLLD','MY9').replace('AETV','AE')
            string = string.replace('APL','Animal Planet').replace('TOON','Cartoon Network').replace('DSC','Discovery').replace('Discovery ','Discovery').replace('BRAVO','Bravo').replace('SYFY','Syfy').replace('HISTORY','History').replace('NATIONAL GEOGRAPHIC','National Geographic')
            string = string.replace('COMEDY','Comedy Central').replace('FOOD','Food Network').replace('NIK','Nickelodeon').replace('LIFE','Lifetime').replace('SPIKETV','SPIKE TV').replace('FNC','Fox News').replace('NGC','National Geographic').replace('Channel','')
            return self.cleanChannel(string)


        def cleanChannel(self, string):
            string = string.replace('WLYH','CW').replace('WHTM','ABC').replace('WPMT','FOX').replace('WPSU','PBS').replace('WHP','CBS').replace('WGAL','NBC').replace('My9','MY9').replace('AETV','AE').replace('USA','USA Network').replace('Channel','').replace('Network Network','Network')
            return string.strip()


        def makeXMLTV(self, data, filepath):
            self.log('makeXMLTV')
            finished = False
            if not FileAccess.exists(os.path.dirname(filepath)):
                FileAccess.mkdir(os.path.dirname(filepath))
            if FileAccess.exists(filepath):
                FileAccess.delete(filepath)
            fle = open(filepath, "w")
            try:
                xml = data.toxml(encoding='UTF-8');
                log('writing item: %s' % (filepath))
                if FileAccess.exists(filepath):
                    finished = True
            except Exception as e:
                xml  = '<?xml version="1.0" encoding="UTF-8"?>'
                xml += '<error>' + str(e) + '</error>';
            xmllst = xml.replace('><','>\n<')
            xmllst = self.cleanChanName(xmllst)
            fle.write("%s" % xmllst)
            fle.close()
            return finished
            
except Exception,e:
    self.log("Unknown Initialization exception " + str(e), xbmc.LOGERROR)
    self.log(traceback.format_exc(), xbmc.LOGERROR)          
    buggalo.onExceptionRaised()