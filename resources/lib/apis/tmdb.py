#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2011-2014 Tommy Winther, Kevin S. Graer, Martijn Kaijser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import urllib, urllib2, socket
import unicodedata, sys, re
import xbmc, xbmcgui

from urllib2 import HTTPError, URLError
from language import *
from operator import itemgetter
from resources.lib.Globals import *
from resources.lib.utils import *

# Use json instead of simplejson when python v2.7 or greater
if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

API_KEY = TMDB_API_KEY
API_CFG = 'http://api.themoviedb.org/3/configuration?api_key=%s'
API_URL = 'http://api.themoviedb.org/3/movie/%s/images?api_key=%s'
BASE_IMAGEURL = "http://d3gtl9l2a4fn1j.cloudfront.net/t/p/"

socket.setdefaulttimeout(5)

class TMDB(object):
    def __init__(self):
        self.name = 'TMDB'
        self.apikey = TMDB_API_KEY
        self.baseurl = 'http://api.themoviedb.org/3'
        try:
            self.imagebaseurl = self._getPosterBaseUrl()
        except Exception,e:
            pass

            
    def _buildUrl(self, cmd, parms={}):
        parmsCopy = parms.copy()
        parmsCopy.update({'api_key' : self.apikey})
        url = '%s/%s?%s' % (self.baseurl, cmd, urllib.urlencode(parmsCopy))
        return url

        
    def _getPosterBaseUrl(self):
        response = json.loads(urllib2.urlopen(urllib2.Request(self._buildUrl('configuration'), {"Accept": "application/json"})).read())
        #self.xbmc.log('Response: \r\n%s' % response)
        return response['images']['base_url']

        
    def getPosterUrl(self, filename):
        return '%s%s%s' % (self.imagebaseurl, 'w92/', filename)

        
    def getMovie(self, movieName, year):
        try:
            response = json.loads(read_url_cached_monthly(self._buildUrl('search/movie', {'query' : movieName, 'year' : year})))
            if response['total_results'] > 0:
                response = json.loads(read_url_cached_monthly(self._buildUrl('movie/%s' % (response['results'][0]['id']), {"Accept": "application/json"})))
            else:
                response = json.loads('{"imdb_id":"", "poster_path":""}')
        except:
            response = ''
        return response

        
    def getMPAA(self, imdbid):
        response = json.loads(read_url_cached_monthly(self._buildUrl('https://api.themoviedb.org/3/movie/'+imdbid+'/releases?api_key='+self.apikey+'&language=en', {"Accept": "application/json"})))
        response = response.split("certification': u'")[1]
        response = response.split("'}")[0]
        return response
        
        
    def getIMDBId(self, movieName, year):
        response = self.getMovie(movieName, year)
        return response['imdb_id']

        
    def getPlot(self, movieName, year):
        response = self.getMovie(movieName, year)
        return response['overview']

        
    def getTagline(self, movieName, year):
        response = self.getMovie(movieName, year)
        return response['tagline']

        
    def getGenre(self, movieName, year):
        response = self.getMovie(movieName, year)
        return response['genres']


    def get_image_list(self, media_id):
        log("tmdb: get_image_list")
        image_list = []
        api_cfg = get_data(API_CFG%(API_KEY), 'json')
        if api_cfg == "Empty" or not api_cfg:
            return image_list
        BASE_IMAGEURL = api_cfg['images'].get('base_url')
        data = get_data(API_URL%(media_id, API_KEY), 'json')
        if data == "Empty" or not data:
            return image_list
        else:
            # Get fanart
            try:
                for item in data['backdrops']:
                    if int(item.get('vote_count')) >= 1:
                        rating = float( "%.1f" % float( item.get('vote_average'))) #output string with one decimal
                        votes = item.get('vote_count','n/a')
                    else:
                        rating = 'n/a'
                        votes = 'n/a'
                    image_list.append({'url': BASE_IMAGEURL + 'original' + item['file_path'],
                                       'preview': BASE_IMAGEURL + 'w300' + item['file_path'],
                                       'id': item.get('file_path').lstrip('/').replace('.jpg', ''),
                                       'art_type': ['fanart','extrafanart'],
                                       'height': item.get('height'),
                                       'width': item.get('width'),
                                       'language': item.get('iso_639_1','n/a'),
                                       'rating': rating,
                                       'votes': votes,
                                       'generalinfo': ('%s: %s  |  %s: %s  |  %s: %s  |  %s: %sx%s  |  ' 
                                                        %( "Language", get_language(item.get('iso_639_1','n/a')).capitalize(),
                                                           "Rating", rating,
                                                           "Votes", votes,
                                                           "Size", item.get('width'), item.get('height')))})
            except Exception, e:
                xbmc.log( 'Problem report: %s' %str( e ), xbmc.LOGNOTICE )
            # Get thumbs
            try:
                for item in data['backdrops']:
                    if int(item.get('vote_count')) >= 1:
                        rating = float( "%.1f" % float( item.get('vote_average'))) #output string with one decimal
                        votes = item.get('vote_count','n/a')
                    else:
                        rating = 'n/a'
                        votes = 'n/a'
                    # Fill list
                    image_list.append({'url': BASE_IMAGEURL + 'w780' + item['file_path'],
                                       'preview': BASE_IMAGEURL + 'w300' + item['file_path'],
                                       'id': item.get('file_path').lstrip('/').replace('.jpg', ''),
                                       'art_type': ['extrathumbs'],
                                       'height': item.get('height'),
                                       'width': item.get('width'),
                                       'language': item.get('iso_639_1','n/a'),
                                       'rating': rating,
                                       'votes': votes,
                                       'generalinfo': ('%s: %s  |  %s: %s  |  %s: %s  |  %s: %sx%s  |  ' 
                                                       %( "Language", get_language(item.get('iso_639_1','n/a')).capitalize(),
                                                          "Rating", rating,
                                                          "Votes", votes,
                                                          "Size", item.get('width'), item.get('height')))})
            except Exception, e:
                xbmc.log( 'Problem report: %s' %str( e ), xbmc.LOGNOTICE )
            # Get posters
            try:
                for item in data['posters']:
                    if int(item.get('vote_count')) >= 1:
                        rating = float( "%.1f" % float( item.get('vote_average'))) #output string with one decimal
                        votes = item.get('vote_count','n/a')
                    else:
                        rating = 'n/a'
                        votes = 'n/a'
                    # Fill list
                    image_list.append({'url': BASE_IMAGEURL + 'original' + item['file_path'],
                                       'preview': BASE_IMAGEURL + 'w185' + item['file_path'],
                                       'id': item.get('file_path').lstrip('/').replace('.jpg', ''),
                                       'art_type': ['poster'],
                                       'height': item.get('height'),
                                       'width': item.get('width'),
                                       'language': item.get('iso_639_1','n/a'),
                                       'rating': rating,
                                       'votes': votes,
                                       # Create Gui string to display
                                       'generalinfo': ('%s: %s  |  %s: %s  |  %s: %s  |  %s: %sx%s  |  ' 
                                                       %( "Language", get_language(item.get('iso_639_1','n/a')).capitalize(),
                                                          "Rating", rating,
                                                          "Votes", votes,
                                                          "Size", item.get('width'), item.get('height')))})
            except Exception, e:
                log( 'Problem report: %s' %str( e ), xbmc.LOGNOTICE )
            
            if image_list != []:
                # Sort the list before return. Last sort method is primary
                image_list = sorted(image_list, key=itemgetter('rating'), reverse=True)
                image_list = sorted(image_list, key=itemgetter('language'))
            return image_list


def _search_movie(medianame,year=''):
    medianame = normalize_string(medianame)
    log('TMDB API search criteria: Title[''%s''] | Year[''%s'']' % (medianame,year) )
    illegal_char = ' -<>:"/\|?*%'
    for char in illegal_char:
        medianame = medianame.replace( char , '+' ).replace( '++', '+' ).replace( '+++', '+' )

    search_url = 'http://api.themoviedb.org/3/search/movie?query=%s+%s&api_key=%s' %( medianame, year, API_KEY )
    tmdb_id = ''
    log('TMDB API search:   %s ' % search_url)
    try:
        data = get_data(search_url, 'json')
        if data == "Empty":
            tmdb_id = ''
        else:
            for item in data['results']:
                if item['id']:
                    tmdb_id = item['id']
                    break
    except Exception, e:
        log( str( e ), xbmc.LOGERROR )
    if tmdb_id == '':
        log('TMDB API search found no ID')
    else:
        log('TMDB API search found ID: %s' %tmdb_id)
    return tmdb_id