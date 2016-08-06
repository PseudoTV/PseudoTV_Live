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
import sys, xbmc, xbmcgui
import unicodedata, urllib, urllib2, socket, traceback

# Use json instead of simplejson when python v2.7 or greater
if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

from operator import itemgetter
from resources.lib.Globals import *
from urllib2 import HTTPError, URLError
from resources.lib.utils import *
from language import *
 
API_KEY = FANARTTV_API_KEY
API_URL_TV = 'http://webservice.fanart.tv/v3/tv/%s?api_key=%s'
API_URL_MOVIE = 'http://webservice.fanart.tv/v3/movies/%s?api_key=%s'
# API_URL_TV = 'http://api.fanart.tv/webservice/series/%s/%s/json/all/1/2'
# API_URL_MOVIE = 'http://api.fanart.tv/webservice/movie/%s/%s/json/all/1/2/'

IMAGE_TYPES_MOVIES = ['clearlogo',
                      'clearart',
                      'hdclearart',
                      'movielogo',
                      'hdmovielogo',
                      'movieart',
                      'moviedisc',
                      'hdmovieclearart',
                      'moviethumb',
                      'moviebanner']

IMAGE_TYPES_SERIES = ['clearlogo',
                      'hdtvlogo',
                      'clearart',
                      'hdclearart',
                      'tvthumb',
                      'seasonthumb',
                      'characterart',
                      'tvbanner',
                      'seasonbanner']
                      
IMAGE_TYPES = ['clearlogo',
               'hdtvlogo',
               'tvposter',
               'seasonposter',
               'showbackground',
               'clearart',
               'hdclearart',
               'tvthumb',
               'seasonthumb',
               'characterart',
               'tvbanner',
               'seasonbanner',
               'movielogo',
               'hdmovielogo',
               'movieart',
               'moviedisc',
               'hdmovieclearart',
               'moviethumb',
               'moviebanner']
  
socket.setdefaulttimeout(5)
             
class fanarttv:
    def __init__(self):
        self.name = 'fanart.tv - TV API'
               

    def get_image_list_TV(self, media_id):
        log("fanarttv: get_image_list_TV")
        image_list = []   
        try:
            data = get_data(API_URL_TV%(media_id,API_KEY), 'json')
            if data == 'Empty' or not data:
                return image_list
            else:
                for value in data.iteritems():
                    for art in IMAGE_TYPES_SERIES:
                        if art == value[0]:
                            for item in value[1]:
                                # Check on what type and use the general tag
                                arttypes = {'clearlogo': 'logo',
                                            'hdtvlogo': 'logo',
                                            'tvposter': 'poster',
                                            'clearart': 'clearart',
                                            'hdclearart': 'clearart',
                                            'tvthumb': 'landscape',
                                            'seasonthumb': 'seasonlandscape',
                                            'characterart': 'characterart',
                                            'tvbanner': 'banner',
                                            'seasonbanner': 'seasonbanner',
                                            'showbackground': 'fanart',
                                            }
                                if art in ['hdtvlogo', 'hdclearart']:
                                    size = 'HD'
                                elif art in ['clearlogo', 'clearart']:
                                    size = 'SD'
                                else:
                                    size = ''
                                # Create GUI info tag
                                generalinfo = '%s: %s  |  ' %( 'Language', get_language(item.get('lang')).capitalize())
                                if item.get('season'):
                                    generalinfo += '%s: %s  |  ' %( 'Season', item.get('season'))
                                generalinfo += '%s: %s  |  ' %( 'Votes', item.get('likes'))
                                if art in ['hdtvlogo', 'hdclearart', 'clearlogo', 'clearart']:
                                    generalinfo += '%s: %s  |  ' %( 'Size', size)
                                # Fill list
                                image_list.append({'url': urllib.quote(item.get('url'), ':/'),
                                                   'preview': item.get('url') + '/preview',
                                                   'id': item.get('id'),
                                                   'art_type': [arttypes[art]],
                                                   'size': size,
                                                   'season': item.get('season','n/a'),
                                                   'language': item.get('lang'),
                                                   'votes': item.get('likes'),
                                                   'generalinfo': generalinfo})
        except Exception,e:
            log("fanarttv: get_image_list_TV, Failed! " + str(e))  
            log(traceback.format_exc(), xbmc.LOGERROR)
            
        if image_list != []:
            # Sort the list before return. Last sort method is primary
            image_list = sorted(image_list, key=itemgetter('votes'), reverse=True)
            image_list = sorted(image_list, key=itemgetter('size'), reverse=False)
            image_list = sorted(image_list, key=itemgetter('language'))
        return image_list


    def get_image_list_Movie(self, media_id):
        log("fanarttv: get_image_list_Movie")
        image_list = []   
        try:
            data = get_data(API_URL_MOVIE%(media_id, API_KEY), 'json')
            if data == 'Empty' or not data:
                return image_list
            else:
                for value in data.iteritems():
                    for art in IMAGE_TYPES_MOVIES:
                        if art == value[0]:
                            for item in value[1]:
                                # Check on what type and use the general tag
                                arttypes = {'movielogo': 'clearlogo',
                                            'moviedisc': 'discart',
                                            'movieart': 'clearart',
                                            'hdmovielogo': 'clearlogo',
                                            'hdmovieclearart': 'clearart',
                                            'moviebanner': 'banner',
                                            'moviethumb': 'landscape'}
                                if art in ['hdmovielogo', 'hdmovieclearart']:
                                    size = 'HD'
                                elif art in ['movielogo', 'movieart']:
                                    size = 'SD'
                                else:
                                    size = ''
                                generalinfo = '%s: %s  |  ' %( 'Language', get_language(item.get('lang')).capitalize())
                                if item.get('disc_type'):
                                    generalinfo += '%s: %s (%s)  |  ' %( 'Disc', item.get('disc'), item.get('disc_type'))
                                if art in ['hdmovielogo', 'hdmovieclearart', 'movielogo', 'movieclearart']:
                                    generalinfo += '%s: %s  |  ' %( 'Size', size)
                                generalinfo += '%s: %s  |  ' %( 'Votes', item.get('likes'))
                                # Fill list
                                image_list.append({'url': urllib.quote(item.get('url'), ':/'),
                                                   'preview': item.get('url') + '/preview',
                                                   'id': item.get('id'),
                                                   'art_type': [arttypes[art]],
                                                   'size': size,
                                                   'season': item.get('season','n/a'),
                                                   'language': item.get('lang'),
                                                   'votes': item.get('likes'),
                                                   'disctype': item.get('disc_type','n/a'),
                                                   'discnumber': item.get('disc','n/a'),
                                                   'generalinfo': generalinfo})
        except Exception,e:
            log("fanarttv: get_image_list_Movie, Failed! " + str(e))  
            log(traceback.format_exc(), xbmc.LOGERROR)
            
        if image_list != []:
            # Sort the list before return. Last sort method is primary
            image_list = sorted(image_list, key=itemgetter('votes'), reverse=True)
            image_list = sorted(image_list, key=itemgetter('size'), reverse=False)
            image_list = sorted(image_list, key=itemgetter('language'))
        return image_list