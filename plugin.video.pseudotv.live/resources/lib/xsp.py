#   Copyright (C) 2024 Lunatixz
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

from globals          import *
from library          import Library
from xml.dom.minidom  import parse, parseString, Document

class XSP:
    def __init__(self):
        self.cache = Cache()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def isXSP(self, path):
        if path.lower().endswith('.xsp'): return True
        return False
        
    
    def isDXSP(self, path):
        if '?xsp=' in path.lower(): return True
        return False
        
        
    def getSmartPlaylistName(self, fle):
        try:
            name = ''
            fle = fle.strip('/').replace('library://','special://userdata/library/')
            xml = FileAccess.open(fle, "r")
            string = xml.read()
            xml.close()
            if fle.endswith('xml'): key = 'label'
            else: key = 'name'
            match = re.compile('<%s>(.*?)\</%s>'%(key,key), re.IGNORECASE).search(string)
            if match: name =  unescapeString(match.group(1))
            self.log("getSmartPlaylistName fle = %s, name = %s"%(fle,name))
        except: self.log("getSmartPlaylistName return unable to parse %s"%(fle), xbmc.LOGERROR)
        return name


    def findSmartPlaylist(self, name):
        self.log("findSmartPlaylist, name = %s"%(name))
        library   = Library()
        playlists = library.getPlaylists()
        del library
        for item in playlists:
            if item.get('name','').lower() == name.lower():
                self.log("findSmartPlaylist, found = %s"%(item.get('path')))
                return item.get('path')
            

    def parseSmartPlaylist(self, file):
        self.log("parseSmartPlaylist, file = %s"%(file))
        paths  = []
        sort   = {}
        filter = {}

        try: 
            xml = FileAccess.open(file, "r")
            dom = parse(xml)
            xml.close()
            
            #media
            try:    media = 'music' if dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value.lower() in MUSIC_TYPES else 'video'
            except: media = 'video'
            #paths
            try:#todo use operators to build filter list for mixed content.
                if dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value.lower() == "mixed":
                    for rule in dom.getElementsByTagName('rule'):
                        if rule.getAttribute('field').lower() == 'path' and rule.getAttribute('operator').lower() in ['is','contains']:
                            paths.append(rule.getElementsByTagName("value")[0].childNodes[0].data)
                        elif rule.getAttribute('field').lower() in ['playlist','virtualfolder'] and rule.getAttribute('operator').lower() in ['is','contains']:
                            paths.extend(self.findSmartPlaylist(rule.getElementsByTagName("value")[0].childNodes[0].data))
            except: pass
            #sort
            try: sort["method"] = dom.getElementsByTagName('order')[0].childNodes[0].nodeValue.lower()#todo pop rules to filter var.
            except: pass
            try: sort["order"] = dom.getElementsByTagName('order')[0].getAttribute('direction').lower()#todo pop rules to filter var.
            except: pass
            self.log("parseSmartPlaylist, media = %s, paths = %s, sort = %s"%(media, paths, sort))
        except Exception as e: self.log("parseSmartPlaylist, failed! %s"%(e), xbmc.LOGERROR)
        return paths, filter, media, sort


    def parseDynamicPlaylist(self, path):
        sort   = {}
        filter = {}
        media  = 'video'
        try:
            media = 'music' if path.lower().startswith('musicdb://') else 'video'
            url, params = path.split('?xsp=')
            payload = loadJSON(params)
            if payload: 
                path = url
                if payload.get('order'): sort   = payload.pop('order')
                if payload.get('rules'): filter = payload.pop('rules')
            self.log("parseDynamicPlaylist, path = %s, media = %s, sort = %s, filter = %s"%(path, media, sort, filter))
        except Exception as e: self.log("parseDynamicPlaylist, failed! %s"%(e), xbmc.LOGERROR)
        return path, filter, media, sort
        
        
    def buildDynamicPlaylist(self):
        # https://github.com/xbmc/xbmc/blob/master/xbmc/playlists/SmartPlayList.cpp
        params = {}
        def type():
            enumLST = ['songs', 'albums', 'artists', 'movies', 'tvshows', 'episodes', 'musicvideos', 'mixed']
            select  = DIALOG.selectDialog(enumLST)
            if select: params['type'] = enumLST[select]
            
        def andor():
            enumLST = ['and', 'or']
            select  = DIALOG.selectDialog(enumLST)
            if select: params.setdefault('rules',{})[enumLST[select]] = []

        def field(rules): #rules = {"and":[]}
            if params['type'] == 'songs':
                enumLST = ['Genre', 'Source', 'Album', 'Artist', 'AlbumArtist', 'Title', 'Year', 'Time', 'TrackNumber', 'Filename', 'Path', 'Playcount', 'LastPlayed', 'Rating', 'UserRating', 'Comment', 'Moods']
            elif params['type'] ==  'albums':
                enumLST = ['Genre', 'Source', 'Album', 'Artist', 'AlbumArtist', 'Year', 'Review', 'Themes', 'Moods', 'Styles', 'Compilation', 'AlbumType', 'MusicLabel', 'Rating', 'UserRating', 'Playcount', 'LastPlayed', 'Path']
            elif params['type'] ==  'artists':
                enumLST = ['Artist', 'Source', 'Genre', 'Moods', 'Styles', 'Instruments', 'Biography', 'ArtistType', 'Gender', 'Disambiguation', 'Born', 'BandFormed', 'Disbanded', 'Died', 'Role', 'Path']
            elif params['type'] ==  'tvshows':
                enumLST = ['Title', 'OriginalTitle', 'Plot', 'TvShowStatus', 'Votes', 'Rating', 'UserRating', 'Year', 'Genre', 'Director', 'Actor', 'NumberOfEpisodes', 'NumberOfWatchedEpisodes', 'Playcount', 'Path', 'Studio', 'MPAA', 'DateAdded', 'LastPlayed', 'InProgress', 'Tag']
            elif params['type'] ==  'episodes':
                enumLST = ['Title', 'TvShowTitle', 'OriginalTitle', 'Plot', 'Votes', 'Rating', 'UserRating', 'Time', 'Writer', 'AirDate', 'Playcount', 'LastPlayed', 'InProgress', 'Genre', 'Year', 'Premiered', 'Director', 'Actor', 'EpisodeNumber', 'Season', 'Filename', 'Path', 'Studio', 'Mpaa', 'DateAdded', 'Tag', 'VideoResolution', 'AudioChannels', 'AudioCount', 'SubtitleCount', 'VideoCodec', 'AudioCodec', 'AudioLanguage', 'SubtitleLanguage', 'VideoAspectRatio']
            elif params['type'] ==  'movies':
                enumLST = ['Title', 'OriginalTitle', 'Plot', 'PlotOutline', 'Tagline', 'Votes', 'Rating', 'UserRating', 'Time', 'Writer', 'Playcount', 'LastPlayed', 'InProgress', 'Genre', 'Country', 'Year', 'Premiered', 'Director', 'Actor', 'Mpaa', 'Top250', 'Studio', 'Trailer', 'Filename', 'Path', 'Set', 'Tag', 'DateAdded', 'VideoResolution', 'AudioChannels', 'AudioCount', 'SubtitleCount', 'VideoCodec', 'AudioCodec', 'AudioLanguage', 'SubtitleLanguage', 'VideoAspectRatio']
            elif params['type'] == 'musicvideos':
                enumLST = ['Title', 'Genre', 'Album', 'Year', 'Artist', 'Filename', 'Path', 'Playcount', 'LastPlayed', 'Rating', 'UserRating', 'Time', 'Director', 'Studio', 'Plot', 'Tag', 'DateAdded', 'VideoResolution', 'AudioChannels', 'AudioCount', 'SubtitleCount', 'VideoCodec', 'AudioCodec', 'AudioLanguage', 'SubtitleLanguage', 'VideoAspectRatio']
            else:
                enumLST = ['Playlist', 'VirtualFolder']
            select = DIALOG.selectDialog(enumLST)
            if select: rules.append(operator({"field":enumLST[select]}))
            params['rules'].update(rules)
            
        def operator(rule): #rule = {"field":""}    
            enumLST = ['contains', 'doesnotcontain', 'is', 'isnot', 'startswith', 'endswith', 'lessthan', 'greaterthan', 'after', 'before']
            if rule["field"] == 'date': enumLST.extend(['inthelast', 'notinthelast'])
            select = DIALOG.selectDialog(enumLST)
            if select: rule.update({"operator":enumLST[select]})
            return value(rule)
            
        def value(rule): #rule = {"field":"","operator":""}    
            KEY_INPUT = {'Title':DIALOG.inputDialog,
                         'Path' :DIALOG.browseDialog,
                         'Genre':DIALOG.selectDialog,
                         None   : None}
            input = KEY_INPUT.get(rule.get('field'))()
            if input: rule.update({"value":input[select]})
            return rule
            
        # # example* source = 
        # #    *  '{"rules":{"and":[{"field":"%s","operator":"%s","value":["%s"]}]},"type":"%s"}' % (field,operator,field_value,xsp_type)
        # #    *  '{"rules":{"and":[{"field":"actor","operator":"contains","value":["$VAR[videoinfo_cast_container_id]"]},{"field":"title","operator":"isnot","value":["$INFO[Window(home).Property(EncodedTitle)]"]}]},"type":"movies"}'
        # source = '{"rules":{"%s":[%s]},"type":"%s"}' % (match,xsp_rules,xsp_type)

        # # experimental : set db_url_root_path 
        # if xsp_type == 'movies' or xsp_type == 'tvshows' or xsp_type == 'episodes' or xsp_type == 'musicvideos' or xsp_type == 'videos':
            # db = 'videodb'
        # else:
            # db = 'musicdb'
        # # else: files\\ ??
        
        # if xsp_type == 'movies' or xsp_type == 'tvshows' or xsp_type == 'musicvideos':
            # db_url_root_path = "%s://%s/titles/?xsp=" % (db,xsp_type)
        
        # elif xsp_type == 'episodes':
            # db_url_root_path = f"{db}://tvshows/titles/-1/-1/?xsp="
        
        # else:
            # db_url_root_path = "%sdb://%s/?xsp=" % (db,xsp_type)

    # # decode
    # # example source = '%7B%22rules%22%3A%7B%22and%22%3A%5B%7B%22field%22%3A%22actor%22%2C%22operator%22%3A%22is%22%2C%22value%22%3A%5B%22christian%20bale%22%5D%7D%5D%7D%2C%22type%22%3A%22movies%22%7D'

if __name__ == '__main__':
    main()