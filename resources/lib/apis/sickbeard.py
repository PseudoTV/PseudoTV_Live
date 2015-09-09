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
import urllib, urllib2, json
import resources.lib.Globals

# Commoncache plugin import
try:
    import StorageServer
except:
    import resources.lib.storageserverdummy as StorageServer

# import libraries
from urllib2 import HTTPError, URLError
from resources.lib.Globals import *
from resources.lib.utils import *

class SickBeard(object):
    def __init__(self, base_url='http://localhost:8081', api_key='cf6a9873e3f6dd25abbb654c7e362d9d'):
        self.apikey = api_key
        self.baseurl = base_url

    def __repr__(self):
        return '[script.tvguide.SickBeard] SickBeard(base_url=%s, apikey=%s)' % (self.baseurl, self.apikey)

    def _buildUrl(self, cmd, parms={}):
        parmsCopy = parms.copy()
        parmsCopy.update({'cmd' : cmd})
        url = '%s/api/%s/?%s' % (self.baseurl, self.apikey, urllib.urlencode(parmsCopy))
        #self.xbmc.log(url)
        return url

    def isShowManaged(self, tvdbid):
        xbmc.log("script.pseudotv.live-sickbeard: isShowManaged Creating Cache")
        response = json.load(urllib.urlopen(self._buildUrl('show', {'tvdbid' : tvdbid})))
        return response['result'] == 'success'

    def addNewShow(self, tvdbid, flatten=0, status='skipped'):
        if not self.isShowManaged(tvdbid):
            response = json.load(urllib.urlopen(self._buildUrl('show.addnew', {'tvdbid' : tvdbid, 'flatten_folders' : flatten, 'status' : status})))
            #self.xbmc.log('tvdbid=%s, flatten=%s, status=%s, result=%s' % (tvdbid, flatten, status, response['result']))
            return response['result'] == 'success'
        else:
            return False

    # Get the show ID numbers
    def getShowIds(self):
        show_ids=[]
        result=json.load(urllib.urlopen(self._buildUrl('shows', {})))
        for each in result['data']:
            show_ids.append(each)
        return show_ids

    # Get show info dict, key:show_name value:tvdbid
    def getShowInfo(self, show_ids):
        show_info={}
        for id in show_ids:
            result=json.load(urllib.urlopen(self._buildUrl('show', {'tvdbid' : id})))
            name=result['data']['show_name']
            paused=result['data']['paused']
            show_info[name] = [id, paused]
        return show_info

    # Returns the details of a show from Sickbeard 
    def getShowDetails(self, tvdbid):
        result=json.load(urllib.urlopen(self._buildUrl('show', {'tvdbid' : tvdbid})))
        details=result['data']
        
        result=json.load(urllib.urlopen(self._buildUrl('show.stats', {'tvdbid' : tvdbid})))
        total=result['data']['total']
        
        return details, total

    # Return a list of season numbers
    def getSeasonNumberList(self, tvdbid):
        result=json.load(urllib.urlopen(self._buildUrl('show.seasonlist', {'tvdbid' : tvdbid})))
        season_number_list = result['data']
        season_number_list.sort()
        return season_number_list

    # Get the list of episodes ina given season
    def getSeasonEpisodeList(self, tvdbid, season):
        season = str(season)
        result=json.load(urllib.urlopen(self._buildUrl('show.seasons', {'tvdbid' : tvdbid, 'season' : season})))
        season_episodes = result['data']
            
        for key in season_episodes.iterkeys():
            if int(key) < 10:
                newkey = '{0}'.format(key.zfill(2))
                if newkey not in season_episodes:
                    season_episodes[newkey] = season_episodes[key]
                    del season_episodes[key]
        
        return season_episodes

    # Gets the show banner from Sickbeard    
    def getShowBanner(self, tvdbid):
        result = self.baseurl+'/showPoster/?show='+str(tvdbid)+'&which=banner'
        return result

    # Check if there is a cached thumbnail to use, if not use Sickbeard poster
    def getShowPoster(self, tvdbid):
        return self.baseurl+'/showPoster/?show='+str(tvdbid)+'&which=poster'

    # Get list of upcoming episodes
    def getFutureShows(self):
        result=json.load(urllib.urlopen(self._buildUrl('future', {'sort' : 'date', 'type' : 'today|soon'})))
        future_list = result['data']
        return future_list

    # Return a list of the last 20 snatched/downloaded episodes    
    def getHistory(self):
        result=json.load(urllib.urlopen(self._buildUrl('history', {'limit' : 20})))
        history = result['data']
        return history

    # Search the tvdb for a show using the Sickbeard API    
    def searchShowName(self, name):
        search_results = []
        result=json.load(urllib.urlopen(self._buildUrl('sb.searchtvdb', {'name' : name, 'lang' : 'en'})))
        for each in result['data']['results']:
            search_results.append(each)
        return search_results

    # Return a list of the default settings for adding a new show
    def getDefaults(self):
        defaults_result = json.load(urllib.urlopen(self._buildUrl('sb.getdefaults', {})))
        print defaults_result.keys()
        defaults_data = defaults_result['data']
        defaults = [defaults_data['status'], defaults_data['flatten_folders'], str(defaults_data['initial'])]
        return defaults

    # Return a list of the save paths set in Sickbeard
    def getRoodDirs(self):
        directory_result = json.load(urllib.urlopen(self._buildUrl('sb.getrootdirs', {})))
        directory_result = directory_result['data']
        return directory_result

    # Get the version of Sickbeard
    def getSickbeardVersion(self):
        result=json.load(urllib.urlopen(self._buildUrl('sb', {})))
        version = result['data']['sb_version']
        return version

    # Set the status of an episode
    def setEpisodeStatus(self, tvdbid, season, episode, status):
        result = json.load(urllib.urlopen(self._buildUrl('episode.setstatus', {'tvdbid' : tvdbid, 'season' : season, 'episode' : episode, 'status' : status})))
        #self.xbmc.log('tvdbid=%s, season=%s, episode=%s, status=%s, result=%s' % (tvdbid, season, episode, status, result))
        return result['result'] == 'success'   

    # Return a list of the last 20 snatched/downloaded episodes    
    def forceSearch(self):
        result=json.load(urllib.urlopen(self._buildUrl('sb.forcesearch', {})))
        success = result['result']
        settings.messageWindow("Force Search", "Force search returned "+success)

    def setPausedState(self, paused, tvdbid):
        result=json.load(urllib.urlopen(self._buildUrl('show.pause', {'tvdbid' : tvdbid, 'pause' : paused})))
        message = result['message']
        return message

    def manualSearch(self, tvdbid, season, episode):
        result=json.load(urllib.urlopen(self._buildUrl('episode.search', {'tvdbid' : tvdbid, 'season' : season, 'episode' : episode})))
        message = result['message']
        return message    

    def deleteShow(self, tvdbid):
        result = json.load(urllib.urlopen(self._buildUrl('show.delete', {'tvdbid' : tvdbid})))
        return result['result'] == 'success'   