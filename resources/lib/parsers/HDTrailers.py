#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
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

import json, urllib2
import xbmcaddon, xbmc, xbmcgui, xbmcvfs

from resources.lib.utils import *
from BeautifulSoup import BeautifulSoup
from urllib2 import HTTPError, URLError

MAIN_URL = 'http://www.hd-trailers.net/'
NEXT_IMG = 'http://static.hd-trailers.net/images/mobile/next.png'
PREV_IMG = 'http://static.hd-trailers.net/images/mobile/prev.png'
USER_AGENT = 'XBMC Add-on HD-Trailers.net v1.1.0'

SOURCES = (
    'apple.com',
    'yahoo-redir',
    'yahoo.com',
    'youtube.com',
    'moviefone.com',
    'ign.com',
    'hd-trailers.net',
    'aol.com'
)

def get_latest(page=1):
    xbmc.log("script.pseudotv.live-HDTrailers: get_latest")
    url = MAIN_URL + 'page/%d/' % int(page)
    return _get_movies(url)


def get_most_watched():
    xbmc.log("script.pseudotv.live-HDTrailers: get_most_watched")
    url = MAIN_URL + 'most-watched/'
    return _get_movies(url)


def get_top_ten():
    xbmc.log("script.pseudotv.live-HDTrailers: get_top_ten")
    url = MAIN_URL + 'top-movies/'
    return _get_movies(url)


def get_opening_this_week():
    xbmc.log("script.pseudotv.live-HDTrailers: get_opening_this_week")
    url = MAIN_URL + 'opening-this-week/'
    return _get_movies(url)


def get_coming_soon():
    xbmc.log("script.pseudotv.live-HDTrailers: get_coming_soon")
    url = MAIN_URL + 'coming-soon/'
    return _get_movies(url)


def get_by_initial(initial='0'):
    url = MAIN_URL + 'poster-library/%s/' % initial
    return _get_movies(url)


def get_initials():
    return list('0ABCDEFGHIJKLMNOPQRSTUVWXYZ')


def get_videos(movie_id):
    xbmc.log("script.pseudotv.live-HDTrailers: get_videos")
    url = MAIN_URL + 'movie/%s' % movie_id
    tree = __get_tree(url)

    trailers = []
    clips = []
    section = trailers

    span = tree.find('span', {'class': 'topTableImage'})
    movie = {
        'title': span.img['title'],
        'thumb': span.img['src']
    }

    table = tree.find('table', {'class': 'bottomTable'})
    for tr in table.findAll('tr'):
        if tr.find('td', text='Trailers'):
            section = trailers
            continue
        elif tr.find('td', text='Clips'):
            section = clips
            continue
        elif tr.get('itemprop'):
            res_tds = tr.findAll('td', {'class': 'bottomTableResolution'})
            resolutions = {}
            for td in res_tds:
                if td.a:
                    resolutions[td.a.string] = td.a['href']
            if not resolutions:
##                 xbmc.log('No resolutions found: %s' % movie_id)
                continue
            try:
                source = __detect_source(resolutions.values()[0])
            except NotImplementedError, video_url:
##                 xbmc.log('Skipping: %s - %s' % (movie_id, video_url))
                continue
            section.append({
                'title': tr.contents[3].span.string,
                'date': __format_date(tr.contents[1].string),
                'source': source,
                'resolutions': resolutions
            })
    return movie, trailers, clips


def get_yahoo_url(vid, res):
    data_url = (
        "http://video.query.yahoo.com/v1/public/yql?"
        "q=SELECT+*+FROM+yahoo.media.video.streams+WHERE+id='%(video_id)s'+"
        "AND+format='mp4'+AND+protocol='http'+"
        "AND+plrs='sdwpWXbKKUIgNzVhXSce__'+AND+"
        "region='US'&env=prod&format=json"
    )
    data = __get_json(data_url % {'video_id': vid})
    media = data.get('query', {}).get('results', {}).get('mediaObj', [])
    for stream in media[0].get('streams'):
        if int(stream.get('height')) == int(res):
            return stream['host'] + stream['path']
    raise NotImplementedError


def _get_movies(url):
    xbmc.log("script.pseudotv.live-HDTrailers: _get_movies")
    tree = __get_tree(url)
    movies = [{
        'id': td.a['href'].split('/')[2],
        'title': td.a.img['alt'],
        'thumb': td.a.img['src']
    } for td in tree.findAll('td', 'indexTableTrailerImage') if td.a.img]
    has_next_page = tree.find(
        'a',
        attrs={'class': 'startLink'},
        text=lambda text: 'Next' in text
    ) is not None
    return movies, has_next_page


def __detect_source(url):
    for source in SOURCES:
        if source in url:
            return source
    raise NotImplementedError(url)


def __format_date(date_str):
    y, m, d = date_str.split('-')
    return '%s.%s.%s' % (d, m, y)


def __get_tree(url):
    try:
        html = read_url_cached(url)
        tree = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES)
        return tree
    except:
        pass


def __get_json(url):
    try:
        response = read_url_cached(url)
        return json.loads(response)
    except:
        pass

    
def get_playable_url(source, raw_url):
    xbmc.log("script.pseudotv.live-HDTrailers: get_playable_url")
    print source, raw_url
##    print source
    if source == 'apple.com':
        raw_url = '%s' % raw_url
##    elif source == 'yahoo-redir':
##        res = raw_url[-3:]
##        print res
##        raw_url = get_yahoo_url(raw_url, res)
###############################################
##    elif source == 'yahoo-redir':
##        import re
##        vid, res = re.search('id=(.+)&resolution=(.+)', raw_url).groups()
##        raw_url = get_yahoo_url(vid, res)
##############################################
    elif source == 'youtube.com':
        import re
        video_id = re.search(r'v=(.+)&?', raw_url).groups(1)
        raw_url = (
            'plugin://plugin.video.youtube/'
            '?action=play_video&videoid=%s' % video_id
        )
    elif source == 'hd-trailers.net':
        raw_url = raw_url

    return raw_url