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

import sys, os, re, datetime
import urllib, urllib2, socket, cookielib
import simplejson as json
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs

from xml.dom import minidom
from time import time
from xml.etree import ElementTree as ET
from Globals import *
from utils import *

socket.setdefaulttimeout(int(REAL_SETTINGS.getSetting("PlayTimeoutInt")))

class ustvnow:
    def __init__(self):
        self.log('__init__')
        self.mBASE_URL = 'http://m.ustvnow.com'
        self.uBASE_URL = 'http://lv2.ustvnow.com'
        self.user = REAL_SETTINGS.getSetting('ustv_email')
        self.password = REAL_SETTINGS.getSetting('ustv_password')
        self.premium = REAL_SETTINGS.getSetting('ustv_subscription') == "true"
        self.quality_type = int(REAL_SETTINGS.getSetting('ustv_quality_type'))
        self.stream_type = ['rtmp', 'rtsp'][int(REAL_SETTINGS.getSetting('ustv_stream_type'))]
        self.xmltvPath = USTVXML
        self.ActionTimeInt = int(REAL_SETTINGS.getSetting("ActionTimeInt"))
        self.PlayTimeoutInt = int(REAL_SETTINGS.getSetting("PlayTimeoutInt"))
        self.token = self._login()

        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('USTVnow: ' + msg, level)
        
        
    def getToken(self):
        self.log('getToken')
        cnt = 0
        while self.token == 'False':
            self.log('getToken, Working...')
            cnt += 1
            if cnt > int(round((self.PlayTimeoutInt/int(self.ActionTimeInt))))/2:
                return False
            self.token = self._login()
            xbmc.sleep(self.ActionTimeInt)
            self.log('getToken, Retry Count ' + str(cnt)) 
        self.log('getToken, self.token = ' + self.token)    
        return True

        
    def getXMLTV(self):
        self.log('getXMLTV')
        if self.token == 'False':
            self.token = self.getToken()
        return self.makeXMLTV(self.get_guidedata(self.quality_type, self.stream_type),self.xmltvPath)


    def getChannellink(self, chname):
        self.log('getChannellink, chname = ' + chname)
        if self.token == 'False':
            self.token = self.getToken()
        return self.get_link(self.quality_type, self.stream_type, chname)


    def getChannelNames(self):
        self.log('getChannelNames')
        try:
            content = self._get_json('gtv/1/live/listchannels', {'token': self.token, 'l': '1440'})
            channels = []
            results = content['results']['streamnames'];

            for i in range(len(results)):
                name = self.cleanChanName(results[i]['sname'])
                id = results[i]['prgsvcid']
                icon = self.uBASE_URL + '/' + results[i]['img']
                free = results[i]['t'] == 1 # free sub switch 1=free, 0=pay

                if self.premium == True:
                    channels.append([name,icon])
                else:
                    if free:
                        channels.append([name,icon])
            return channels
        except:
            pass


    def _fetch(self, url, form_data=False):
        self.log('_fetch')
        if form_data:
            req = urllib2.Request(url, form_data)
        else:
            req = urllib2.Request(url)
        try:
            response = urllib2.urlopen(req)
            return response
        except urllib2.URLError, e:
            return False


    def _get_json(self, path, queries={}):
        self.log('_get_json')
        content = False
        url = self._build_json(path, queries)
        response = self._fetch(url)
        if response:
            content = json.loads(response.read())
        else:
            content = False
        return content


    def _get_html(self, path, queries={}):
        self.log('_get_html')
        html = False
        url = self._build_url(path, queries)
        # #print url
        response = self._fetch(url)
        if response:
            html = response.read()
        else:
            html = False
        return html


    def build_query(self, queries):
        return '&'.join([k+'='+urllib.quote(str(v)) for (k,v) in queries.items()])


    def _build_url(self, path, queries={}):
        self.log('_build_url')
        if queries:
            query = self.build_query(queries)
            return '%s/%s?%s' % (self.uBASE_URL, path, query)
        else:
            return '%s/%s' % (self.uBASE_URL, path)


    def _build_json(self, path, queries={}):
        self.log('_build_json')
        if queries:
            query = urllib.urlencode(queries)
            return '%s/%s?%s' % (self.mBASE_URL, path, query)
        else:
            return '%s/%s' % (self.mBASE_URL, path)


    def _login(self):
        self.log('_login_NEW')
        token = self._login_ALT()
        if token == 'False':
            token = self._login_ORG()
        return token


    def _login_ALT(self):
        self.log('_login_ALT')
        try:
            self.cj = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
            urllib2.install_opener(opener)
            url = self._build_json('gtv/1/live/login', {'username': self.user,
                                                   'password': self.password,
                                                   'device':'gtv',
                                                   'redir':'0'})
            response = opener.open(url)
            for cookie in self.cj:
                if cookie.name == 'token':
                    return cookie.value
        except:
            pass
        return 'False'


    def _login_ORG(self):
        self.log('_login_ORG')
        try:
            self.cj = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
            urllib2.install_opener(opener)
            url = self._build_url('iphone_login', {'username': self.user,
                                                   'password': self.password})
            response = opener.open(url)
            for cookie in self.cj:
                if cookie.name == 'token':
                    return cookie.value
        except:
            pass
        return 'False'


    def get_link(self, quality, stream_type, chname=False):
        self.log('get_link')
        channels = []
        try:
            html = self._get_html('iphone_ajax', {'tab': 'iphone_playingnow',
                                                  'token': self.token})
            for channel in re.finditer('class="panel".+?title="(.+?)".+?src="' +
                                       '(.+?)".+?class="nowplaying_item">(.+?)' +
                                       '<\/td>.+?class="nowplaying_itemdesc".+?' +
                                       '<\/a>(.+?)<\/td>.+?href="(.+?)"',
                                       html, re.DOTALL):
                show_busy_dialog()
                name, icon, title, plot, url = channel.groups()
                name = name.replace('\n','').replace('\t','').replace('\r','').replace('<fieldset> ','').replace('<div class=','').replace('>','').replace('"','').replace(' ','')
                if not name:
                    name = ((icon.rsplit('/',1)[1]).replace('.png','')).upper()
                    name = self.cleanChanName(name)
                    self.log('get_link, parsing '+ name)
                try:
                    if not url.startswith('http'):
                        link = '%s%s%d' % (stream_type, url[4:-1], quality + 1)
                        if chname != False and chname.lower() == name.lower():
                            hide_busy_dialog()
                            if link == '%s%d' % (stream_type, quality + 1):
                                self.token = 'False'
                                return self.getChannellink(chname)
                            elif not link.startswith(stream_type):
                                return self.getChannellink(chname)
                            self.log('get_link, link = '+link)
                            return link
                        else:
                            channels.append([name, link])
                except:
                    pass
        except:
            pass
        hide_busy_dialog()
        return channels


    def get_channels(self, quality, stream_type):
        self.log('get_channels')
        try:
            result = guide.cacheFunction(self.get_channels_NEW, quality, stream_type)
            if not result:
                raise Exception()
        except:
            result = self.get_channels_NEW(quality, stream_type)
        if not result:
            result = [({
                'name': 'USTVnow is temporarily unavailable, Try again...',
                'sname' : 'callsign',
                'url': 'url',
                'icon': 'img'
                })]
        return result


    def get_channels_NEW(self, quality, stream_type):
        self.log('get_channels_NEW,' + str(quality) + ',' + stream_type)
        channels = []
        content = self._get_json('gtv/1/live/channelguide', {'token': self.token,'format': stream_type, 'l': '1440'})
        results = content['results'];
        for i in results:
            try:
                if i['order'] == 1:
                    name = self.cleanChanName(i['stream_code'])
                    url = "plugin://plugin.video.ustvnow/?name="+name+"&mode=play"
                    mediatype = i['mediatype']
                    poster_url = 'http://mc.ustvnow.com/gtv/1/live/viewposter?srsid=' + str(i['srsid']) + '&cs=' + i['callsign'] + '&tid=' + mediatype
                    mediatype = mediatype.replace('SH', 'tvshow').replace('EP', 'episode').replace('MV', 'movie')
                    if self.premium == False:
                        if name not in ['CW','ABC','FOX','PBS','CBS','NBC','MY9']:
                            raise Exception()
                    channels.append({
                        'name': name,
                        'sname' : i['callsign'],
                        'url': url,
                        'episode_title': i['episode_title'],
                        'title': i['title'],
                        'plot': i['description'],
                        'plotoutline': i['synopsis'],
                        'mediatype': mediatype,
                        'playable': True,
                        'icon': self.uBASE_URL + '/' + i['img'],
                        'poster_url': poster_url
                        })
            except:
                pass
        return channels

        
    def get_guidedata(self, quality, stream_type):
        self.log('get_guidedata')
        try:
            result = guide.cacheFunction(self.get_guidedata_NEW, quality, stream_type)
            if not result:
                raise Exception()
        except:
            self.log('get_guidedata Failed')
            result = self.get_guidedata_NEW(quality, stream_type)
        if not result:
            result = []
        return result


    def get_guidedata_NEW(self, quality, stream_type):
        self.log('get_guidedata_NEW')
        content = self._get_json('gtv/1/live/channelguide', {'token': self.token, 'l': '1440'})
        results = content['results'];
        now = time.time();
        doc = minidom.Document();
        base = doc.createElement('tv');
        base.setAttribute("cache-version", str(now));
        base.setAttribute("cache-time", str(now));
        base.setAttribute("generator-info-name", "IPTV Plugin");
        base.setAttribute("generator-info-url", "http://www.xmltv.org/");
        doc.appendChild(base)
        channels = self.get_channels(quality, stream_type);

        for channel in channels:
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
            start_time 	= datetime.datetime.fromtimestamp(float(programme['ut_start']));
            stop_time	= start_time + datetime.timedelta(seconds=int(programme['guideremainingtime']));

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
        return doc


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
        if not xbmcvfs.exists(os.path.dirname(filepath)):
            xbmcvfs.mkdir(os.path.dirname(filepath))
        if xbmcvfs.exists(filepath):
            xbmcvfs.delete(filepath)
        fle = open(filepath, "w")
        try:
            xml = data.toxml(encoding='utf-8');
            log('writing item: %s' % (filepath))
            if xbmcvfs.exists(filepath):
                finished = True
        except Exception as e:
            xml  = '<?xml version="1.0" encoding="ISO-8859-1"?>'
            xml += '<error>' + str(e) + '</error>';
        xmllst = xml.replace('><','>\n<')
        xmllst = self.cleanChanName(xmllst)
        fle.write("%s" % xmllst)
        fle.close()
        if finished == False:
            self.token = 'False'
            self.getXMLTV()
        return finished