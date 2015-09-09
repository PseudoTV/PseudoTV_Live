#
#      Copyright (C) 2013 Tommy Winther
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
import urllib, urllib2
import json

# Commoncache plugin import
try:
    import StorageServer
except Exception,e:
    import storageserverdummy as StorageServer

# import libraries
from urllib2 import HTTPError, URLError
from resources.lib.utils import *

class CouchPotato(object):
    def __init__(self, base_url='http://localhost:5050', api_key='71e9ea6a3e16430389450eb88e93a8a1'):
        self.apikey = api_key
        self.baseurl = base_url

        
    def _buildUrl(self, cmd, parms={}):
        url = '%s/api/%s/%s/?%s' % (self.baseurl, self.apikey, cmd, urllib.urlencode(parms))
        #xbmc.log(url)
        return url

    
    def addMovie(self, imdbid):
        response = json.load(urllib.urlopen(self._buildUrl('movie.add', {'identifier' : imdbid})))
        #xbmc.log('imdbid=%s, result=%s' % (imdbid, response['added']))
        return response['added'] == 'true'

        
    def getMoviebyTitle(self, title):
        response = json.load(urllib.urlopen(self._buildUrl('movie.list', {'search' : title})))
        return response
        #return self._api_call('movie.list', params).get('movies', [])