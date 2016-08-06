#
#      Copyright (C) 2013 Tommy Winther, Kevin S. Graer, Martijn Kaijser
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#


import sys, re
import urllib, urllib2
import socket, unicodedata
import xbmc, xbmcgui

from urllib2 import HTTPError, URLError
from language import *
from resources.lib.utils import *
from xml.etree import ElementTree as ET
from resources.lib.Globals import *
from resources.lib.utils import *

# Use json instead of simplejson when python v2.7 or greater
if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

API_URL = 'http://www.thetvdb.com/api/%s/series/%s/banners.xml'

socket.setdefaulttimeout(5)

class TVDB(object):
    def __init__(self):
        self.name = 'TVDB'
        self.api_key = TVDB_API_KEY
        self.baseurl = 'http://thetvdb.com'
        self.url_prefix = 'http://www.thetvdb.com/banners/'
    
    
    def _buildUrl(self, cmd, parms={}):
        url = '%s/api/%s?%s' % (self.baseurl, cmd, urllib.urlencode(parms))
        return url

        
    def getIdByZap2it(self, zap2it_id):
        log("tvdb: getIdByZap2it")
        try:
            response = read_url_cached_monthly(self._buildUrl('GetSeriesByRemoteID.php', {'zap2it' : zap2it_id}))
            tvdbidRE = re.compile('<id>(.+?)</id>', re.DOTALL)
            match = tvdbidRE.search(response)
            if match:
                return match.group(1)
            else:
                return '0'
        except Exception,e:
            return '0'

            
    def getIdByIMDB(self, imdb_id):
        log("tvdb: getIdByIMDB")
        try:
            response = read_url_cached_monthly(self._buildUrl('GetSeriesByRemoteID.php', {'apikey' : self.api_key, 'imdbid' : imdb_id}))
            imdbidRE = re.compile('<id>(.+?)</id>', re.DOTALL)
            match = imdbidRE.search(response)

            if match:
                return match.group(1)
            else:
                return 0
        except Exception,e:
            return 0
            
            
    def getEpisodeByAirdate(self, tvdbid, airdate):
        log("tvdb: getEpisodeByAirdate")
        try:
            response = read_url_cached_monthly(self._buildUrl('GetEpisodeByAirDate.php', {'apikey' : self.api_key, 'seriesid' : tvdbid, 'airdate' : airdate}))
            return response
        except Exception,e:
            return ''

            
    def getEpisodeByID(self, tvdbid):
        log("tvdb: getEpisodeByID")
        try:
            response = read_url_cached_monthly(self._buildUrl(self.api_key + '/series/' + tvdbid + '/all/en.xml'))
            return response
        except Exception,e:
            return ''

            
    def getIdByShowName(self, showName):
        log("tvdb: getIdByShowName")
        try:
            #NOTE: This assumes an exact match. It is possible to get multiple results though. This could be smarter
            response = read_url_cached_monthly(self._buildUrl('GetSeries.php', {'seriesname' : showName}))
            tvdbidRE = re.compile('<id>(.+?)</id>', re.DOTALL)
            match = tvdbidRE.search(response)
            if match:
                return match.group(1)
            else:
                return 0
        except Exception,e:
            return 0


    def getBannerByID(self, tvdbid, type):
        log("tvdb: getBannerByID")
        try:
            response = read_url_cached_monthly(self._buildUrl(self.api_key + '/series/' + tvdbid + '/banners.xml'))
            tree = ET.fromstring(response)
            images = []
            banner_data = tree.find("Banners")
            banner_nodes = tree.getiterator("Banner")
            for banner in banner_nodes:
                banner_path = banner.findtext("BannerPath")
                banner_type = banner.findtext("BannerType")
                banner_type2 = banner.findtext("BannerType2")
                if banner_type == 'season':
                    banner_season = banner.findtext("Season")
                else:
                    banner_season = ''
                banner_url = "%s/banners/%s" % ('http://www.thetvdb.com', banner_path)
                if type in banner_path:
                    images.append((banner_url, banner_type, banner_type2, banner_season))
                    break
                # else:
                    # images.append((banner_url, banner_type, banner_type2, banner_season))
            return images
        except Exception,e:
            return ''

    
    def getIMDBbyShowName(self, showName):
        log("tvdb: getIMDBbyShowName")
        try:
            #NOTE: This assumes an exact match. It is possible to get multiple results though. This could be smarter
            response = read_url_cached_monthly(self._buildUrl('GetSeries.php', {'seriesname' : showName}))
            tvdbidRE = re.compile('<IMDB_ID>(.+?)</IMDB_ID>', re.DOTALL)
            match = tvdbidRE.search(response)
            if match:
                return match.group(1)
            else:
                return ''
        except Exception,e:
            return ''


    def get_image_list(self, media_id):
        log("tvdb: get_image_list")
        image_list = []
        data = get_data(API_URL%(self.api_key, media_id), 'xml')
        try:
            tree = ET.fromstring(data)
            for image in tree.findall('Banner'):
                info = {}
                if image.findtext('BannerPath'):
                    info['url'] = self.url_prefix + image.findtext('BannerPath')
                    if image.findtext('ThumbnailPath'):
                        info['preview'] = self.url_prefix + image.findtext('ThumbnailPath')
                    else:
                        info['preview'] = self.url_prefix + image.findtext('BannerPath')
                    info['language'] = image.findtext('Language')
                    info['id'] = image.findtext('id')
                    # process fanarts
                    if image.findtext('BannerType') == 'fanart':
                        info['art_type'] = ['fanart','extrafanart']
                    # process posters
                    elif image.findtext('BannerType') == 'poster':
                        info['art_type'] = ['poster']
                    # process banners
                    elif image.findtext('BannerType') == 'series' and image.findtext('BannerType2') == 'graphical':
                        info['art_type'] = ['banner']
                    # process seasonposters
                    elif image.findtext('BannerType') == 'season' and image.findtext('BannerType2') == 'season':
                        info['art_type'] = ['seasonposter']
                    # process seasonbanners
                    elif image.findtext('BannerType') == 'season' and image.findtext('BannerType2') == 'seasonwide':
                        info['art_type'] = ['seasonbanner']
                    else:
                        info['art_type'] = ['']
                    # convert image size ...x... in Bannertype2
                    if image.findtext('BannerType2'):
                        try:
                            x,y = image.findtext('BannerType2').split('x')
                            info['width'] = int(x)
                            info['height'] = int(y)
                        except:
                            info['type2'] = image.findtext('BannerType2')

                    # check if fanart has text
                    info['series_name'] = image.findtext('SeriesName') == 'true'

                    # find image ratings
                    if int(image.findtext('RatingCount')) >= 1:
                        info['rating'] = float( "%.1f" % float( image.findtext('Rating')) ) #output string with one decimal
                        info['votes'] = image.findtext('RatingCount')
                    else:
                        info['rating'] = 'n/a'
                        info['votes'] = 'n/a'

                    # find season info
                    if image.findtext('Season'):
                        info['season'] = image.findtext('Season')
                    else:
                        info['season'] = 'n/a'

                    info['generalinfo'] = '%s: %s  |  ' %( 'Language', get_language(info['language']).capitalize())
                    if info['season'] != 'n/a':
                        info['generalinfo'] += '%s: %s  |  ' %( 'Season', info['season'] )
                    if 'height' in info:
                        info['generalinfo'] += '%s: %sx%s  |  ' %( 'Size', info['height'], info['width'] )
                    info['generalinfo'] += '%s: %s  |  %s: %s  |  ' %( 'Rating', info['rating'], 'Votes', info['votes'] )

                if info:
                    image_list.append(info)
                    
        except Exception,e:
            log("tvdb: get_image_list, Failed! " + str(e))  
            log(traceback.format_exc(), xbmc.LOGERROR)
            
        if image_list != []:
            # Sort the list before return. Last sort method is primary
            image_list = sorted(image_list, key=itemgetter('rating'), reverse=True)
            image_list = sorted(image_list, key=itemgetter('season'))
            image_list = sorted(image_list, key=itemgetter('language'))
        return image_list