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
#
# -*- coding: utf-8 -*-

import os

from kodi_six      import xbmc, xbmcaddon

#info
ADDON_ID            = 'plugin.video.pseudotv.live'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
ADDON_URL           = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/plugin.video.pseudotv.live/addon.xml'
LANGUAGE            = REAL_SETTINGS.getLocalizedString

#api
MONITOR             = xbmc.Monitor
PLAYER              = xbmc.Player

#constants
DISCOVERY_TIMER     = 60    #secs
EPOCH_TIMER         = 15    #secs
SUSPEND_TIMER       = 15    #secs
DISCOVER_INTERVAL   = 30    #secs
EPG_DURATION        = 10800 #secs
DTFORMAT            = '%Y%m%d%H%M%S'
DTZFORMAT           = '%Y%m%d%H%M%S +%z'
DTJSONFORMAT        = '%Y-%m-%d %H:%M:%S'
LANG                = 'en' #todo parse kodi region settings
DEFAULT_ENCODING    = "utf-8"
PROMPT_DELAY        = 4000 #msecs
AUTOCLOSE_DELAY     = 300  #secs
SELECT_DELAY        = 900  #secs
RADIO_ITEM_LIMIT    = 250
CHANNEL_LIMIT       = 999
AUTOTUNE_LIMIT      = 3
FILLER_LIMIT        = 250

FILLER_TYPE         = ['Rating',
                       'Bumper',
                       'Advert',
                       'Trailer',
                       'Pre-Roll',
                       'Post-Roll']

FILLER_TYPES        = ['Ratings',
                       'Bumpers',
                       'Adverts',
                       'Trailers']
                       
AUTOTUNE_TYPES      = ["Playlists",
                       "TV Networks",
                       "TV Shows",
                       "TV Genres",
                       "Movie Genres",
                       "Movie Studios",
                       "Mixed Genres",
                       "Music Genres",
                       "Mixed",
                       "Recommended",
                       "Services"]

GROUP_TYPES         = ['Addon', 'Directory', 'TV', 'Movies', 'Music', 'Other', 'PVR', 'Plugin', 'Radio', 'Smartplaylist', 'UPNP', 'IPTV'] + AUTOTUNE_TYPES

WEB_TYPES           = ["http",
                       "ftp",
                       "pvr"]

VFS_TYPES           = ["plugin://",
                       "pvr://",
                       "upnp://",
                       "resource://",
                       "special://home/addons/resource"]
                       
TV_TYPES            = ['episode',
                       'episodes',
                       'tvshow',
                       'tvshows']
                       
MOVIE_TYPES         = ['movie',
                       'movies']
                       
MUSIC_TYPES         = ['songs',
                       'albums',
                       'artists',
                       'music']
            
HTML_ESCAPE         = {"&": "&amp;",
                       '"': "&quot;",
                       "'": "&apos;",
                       ">": "&gt;",
                       "<": "&lt;"}    

ALT_PLAYLISTS       = [".cue",
                       ".m3u",
                       ".m3u8",
                       ".strm",
                       ".pls",
                       ".wpl"] 

TV_URL              = 'plugin://{addon}/?mode=tv&name={name}&chid={chid}.pvr'
RADIO_URL           = 'plugin://{addon}/?mode=radio&name={name}&chid={chid}&radio={radio}&vid={vid}.pvr'
LIVE_URL            = 'plugin://{addon}/?mode=live&name={name}&chid={chid}&vid={vid}&now={now}&start={start}&duration={duration}&stop={stop}.pvr'
BROADCAST_URL       = 'plugin://{addon}/?mode=broadcast&name={name}&chid={chid}&vid={vid}.pvr'
VOD_URL             = 'plugin://{addon}/?mode=vod&title={title}&chid={chid}&vid={vid}&name={name}.pvr'
DVR_URL             = 'plugin://{addon}/?mode=dvr&title={title}&chid={chid}&vid={vid}&seek={seek}&duration={duration}.pvr'
              
PTVL_REPO           = 'repository.pseudotv'
PVR_CLIENT_ID       = 'pvr.iptvsimple'
PVR_CLIENT_NAME     = 'IPTV Simple Client'
PVR_CLIENT_LOC      = 'special://profile/addon_data/%s'%(PVR_CLIENT_ID)

#docs
README_FLE          = os.path.join(ADDON_PATH,'README.md')
CHANGELOG_FLE       = os.path.join(ADDON_PATH,'changelog.txt')
LICENSE_FLE         = os.path.join(ADDON_PATH,'LICENSE')

#files
M3UFLE              = 'pseudotv.m3u'
XMLTVFLE            = 'pseudotv.xml'
GENREFLE            = 'genres.xml'
REMOTEFLE           = 'remote.json'
BONJOURFLE          = 'bonjour.json'
SERVERFLE           = 'servers.json'
CHANNELFLE          = 'channels.json'
LIBRARYFLE          = 'library.json'
TVGROUPFLE          = 'tv_groups.xml'
RADIOGROUPFLE       = 'radio_groups.xml'
PROVIDERFLE         = 'providers.xml'
CHANNELBACKUPFLE    = 'channels.backup'
CHANNELRESTOREFLE   = 'channels.restore'

#exts
VIDEO_EXTS          = xbmc.getSupportedMedia('video').split('|')[:-1]
MUSIC_EXTS          = xbmc.getSupportedMedia('music').split('|')[:-1]
IMAGE_EXTS          = xbmc.getSupportedMedia('picture').split('|')[:-1]
IMG_EXTS            = ['.png','.jpg','.gif']
TEXTURES            = 'Textures.xbt'

#folders
IMAGE_LOC           = os.path.join(ADDON_PATH,'resources','images')
MEDIA_LOC           = os.path.join(ADDON_PATH,'resources','skins','default','media')
SFX_LOC             = os.path.join(MEDIA_LOC,'sfx')
SERVER_LOC          = os.path.join(SETTINGS_LOC,SERVERFLE)
BACKUP_LOC          = os.path.join(SETTINGS_LOC,'backup')
CACHE_LOC           = os.path.join(SETTINGS_LOC,'cache')
TEMP_LOC            = os.path.join(SETTINGS_LOC,'temp')

#file paths
SETTINGS_FLE        = os.path.join(SETTINGS_LOC,'settings.xml')
CHANNELFLE_BACKUP   = os.path.join(BACKUP_LOC,CHANNELBACKUPFLE)
CHANNELFLE_RESTORE  = os.path.join(BACKUP_LOC,CHANNELRESTOREFLE)

#sfx
BING_WAV            = os.path.join(SFX_LOC,'bing.wav')
NOTE_WAV            = os.path.join(SFX_LOC,'notify.wav')

#remotes
IMPORT_ASSET        = os.path.join(ADDON_PATH,'remotes','asset.json')
RULEFLE_ITEM        = os.path.join(ADDON_PATH,'remotes','rule.json')
CHANNEL_ITEM        = os.path.join(ADDON_PATH,'remotes','channel.json')
M3UFLE_DEFAULT      = os.path.join(ADDON_PATH,'remotes','m3u.json')
GROUPFLE_DEFAULT    = os.path.join(ADDON_PATH,'remotes','groups.xml')
LIBRARYFLE_DEFAULT  = os.path.join(ADDON_PATH,'remotes',LIBRARYFLE)
CHANNELFLE_DEFAULT  = os.path.join(ADDON_PATH,'remotes',CHANNELFLE)
GENREFLE_DEFAULT    = os.path.join(ADDON_PATH,'remotes',GENREFLE)
PROVIDERFLE_DEFAULT = os.path.join(ADDON_PATH,'remotes',PROVIDERFLE)

#colors
COLOR_BACKGROUND          = '01416b'
COLOR_TEXT                = 'ffffff'
COLOR_UNAVAILABLE_CHANNEL = 'dimgray'
COLOR_AVAILABLE_CHANNEL   = 'white'
COLOR_LOCKED_CHANNEL      = 'orange'
COLOR_WARNING_CHANNEL     = 'red'
COLOR_NEW_CHANNEL         = 'green'
COLOR_RADIO_CHANNEL       = 'cyan'
COLOR_FAVORITE_CHANNEL    = 'yellow'

#urls
URL_WIKI                  = 'https://github.com/PseudoTV/PseudoTV_Live/wiki'
URL_SUPPORT               = 'https://forum.kodi.tv/showthread.php?tid=346803'
URL_WIN_BONJOUR           = 'https://support.apple.com/en-us/106380'
URL_README                = 'https://github.com/PseudoTV/PseudoTV_Live/blob/master/plugin.video.pseudotv.live/README.md'


# https://github.com/xbmc/xbmc/blob/master/system/colors.xml

#images
LOGO                = os.path.join(MEDIA_LOC,'wlogo.png')
COLOR_LOGO          = os.path.join(MEDIA_LOC,'logo.png')
HOST_LOGO           = 'http://github.com/PseudoTV/PseudoTV_Live/blob/master/plugin.video.pseudotv.live/resources/skins/default/media/logo.png?raw=true'
DUMMY_ICON          = 'https://dummyimage.com/512x512/%s/%s.png&text={text}'%(COLOR_BACKGROUND,COLOR_TEXT)
MST3K_1             = os.path.join(MEDIA_LOC,'overlays','MST3K_1.gif')
MST3K_2             = os.path.join(MEDIA_LOC,'overlays','MST3K_2.gif')

#skins
RESTART_XML    = '%s.restart.xml'%(ADDON_ID)
BACKGROUND_XML = '%s.background.xml'%(ADDON_ID)
MANAGER_XML    = '%s.manager.xml'%(ADDON_ID)
CHANNELBUG_XML = '%s.channelbug.xml'%(ADDON_ID)

# https://github.com/xbmc/xbmc/blob/master/xbmc/addons/kodi-dev-kit/include/kodi/c-api/gui/input/action_ids.h

# Actions
ACTION_MOVE_LEFT     = 1
ACTION_MOVE_RIGHT    = 2
ACTION_MOVE_UP       = 3
ACTION_MOVE_DOWN     = 4
ACTION_INVALID       = 999
ACTION_SELECT_ITEM   = [7,135]
ACTION_PREVIOUS_MENU = [92,10,110,521,ACTION_SELECT_ITEM]

#rules
##builder
RULES_ACTION_CHANNEL_CITEM                = 1 
RULES_ACTION_CHANNEL_START                = 2 
RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE  = 3
RULES_ACTION_CHANNEL_BUILD_PATH           = 4
RULES_ACTION_CHANNEL_BUILD_FILELIST       = 5
RULES_ACTION_CHANNEL_BUILD_TIME_PRE       = 7
RULES_ACTION_CHANNEL_BUILD_TIME_POST      = 8
RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST = 9
RULES_ACTION_CHANNEL_STOP                 = 10
##player
RULES_ACTION_PLAYER_START  = 12
RULES_ACTION_PLAYER_CHANGE = 13
RULES_ACTION_PLAYER_STOP   = 14
##overlay/background
RULES_ACTION_OVERLAY_OPEN     = 21
RULES_ACTION_OVERLAY_CLOSE    = 22
RULES_ACTION_BACKGROUND_OPEN  = 23
RULES_ACTION_BACKGROUND_CLOSE = 24

ISPOT_PATHS = ['plugin://plugin.video.ispot.tv']
IMDB_PATHS  = ['plugin://plugin.video.imdb.trailers/?action=list1&key=showing',
               'plugin://plugin.video.imdb.trailers/?action=list1&key=coming']
               
HEADER      = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"}

MUSIC_LISTITEM_TYPES =   {'tracknumber'             : (int,),  #integer (8)
                          'discnumber'              : (int,),  #integer (2)
                          'duration'                : (int,),  #integer (245) - duration in seconds
                          'year'                    : (int,),  #integer (1998)
                          'genre'                   : (tuple,list),  
                          'album'                   : (str,),  
                          'artist'                  : (str,),  
                          'title'                   : (str,),  
                          'rating'                  : (float,),#float - range is between 0 and 10
                          'userrating'              : (int,),  #integer - range is 1..10
                          'lyrics'                  : (str,),
                          'playcount'               : (int,),  #integer (2) - number of times this item has been played
                          'lastplayed'              : (str,),  #string (Y-m-d h:m:s = 2009-04-05 23:16:04)
                          'mediatype'               : (str,),  #string - "music", "song", "album", "artist"
                          'dbid'                    : (int,),  #integer (23) - Only add this for items which are part of the local db. You also need to set the correct 'mediatype'!
                          'listeners'               : (int,),  #integer (25614)
                          'musicbrainztrackid'      : (str,list),
                          'musicbrainzartistid'     : (str,list),
                          'musicbrainzalbumid'      : (str,list),
                          'musicbrainzalbumartistid': (str,list),
                          'comment'                 : (str,),  
                          'count'                   : (int,),  #integer (12) - can be used to store an id for later, or for sorting purposes
                          # 'size'                    : (int,), #long (1024) - size in bytes
                          'date'                    : (str,),} #string (d.m.Y / 01.01.2009) - file date

VIDEO_LISTITEM_TYPES =   {'genre'                   : (tuple,list),
                          'country'                 : (str,list),
                          'year'                    : (int,),  #integer (2009)
                          'episode'                 : (int,),  #integer (4)
                          'season'                  : (int,),  #integer (1)
                          'sortepisode'             : (int,),  #integer (4)
                          'sortseason'              : (int,),  #integer (1)
                          'episodeguide'            : (str,),
                          'showlink'                : (str,list),
                          'top250'                  : (int,),  #integer (192)
                          'setid'                   : (int,),  #integer (14)
                          'tracknumber'             : (int,),  #integer (3)
                          'rating'                  : (float,),#float (6.4) - range is 0..10
                          'userrating'              : (int,),  #integer (9) - range is 1..10 (0 to reset)
                          'playcount'               : (int,),  #integer (2) - number of times this item has been played
                          'overlay'                 : (int,),  #integer (2) - range is 0..7. See Overlay icon types for values
                          'cast'                    : (list,),
                          'castandrole'             : (list,tuple),
                          'director'                : (str,list),
                          'mpaa'                    : (str,),
                          'plot'                    : (str,),
                          'plotoutline'             : (str,),
                          'title'                   : (str,),
                          'originaltitle'           : (str,),
                          'sorttitle'               : (str,),
                          'duration'                : (int,),  #integer (245) - duration in seconds
                          'studio'                  : (str,list),
                          'tagline'                 : (str,),
                          'writer'                  : (str,list),
                          'tvshowtitle'             : (str,list),
                          'premiered'               : (str,),  #string (2005-03-04)
                          'status'                  : (str,),
                          'set'                     : (str,),
                          'setoverview'             : (str,),
                          'tag'                     : (str,list),
                          'imdbnumber'              : (str,),  #string (tt0110293) - IMDb code
                          'code'                    : (str,),  #string (101) - Production code
                          'aired'                   : (str,),  #string (2008-12-07) 
                          'credits'                 : (str,list),
                          'lastplayed'              : (str,),  #string (Y-m-d h:m:s = 2009-04-05 23:16:04)
                          'album'                   : (str,),
                          'artist'                  : (list,),
                          'votes'                   : (str,),
                          'path'                    : (str,),
                          'trailer'                 : (str,),
                          'dateadded'               : (str,),  #string (Y-m-d h:m:s = 2009-04-05 23:16:04)
                          'mediatype'               : (str,),  #mediatype	string - "video", "movie", "tvshow", "season", "episode" or "musicvideo"
                          'dbid'                    : (int,),  #integer (23) - Only add this for items which are part of the local db. You also need to set the correct 'mediatype'!
                          'count'                   : (int,),  #integer (12) - can be used to store an id for later, or for sorting purposes
                          # 'size'                    : (int,),  #long (1024) - size in bytes
                          'date'                    : (str,),} #string (d.m.Y / 01.01.2009) - file date

IGNORE_CHTYPE = ['TV Shows','Mixed','Recommended','Services',"Music Genres"]
MOVIE_CHTYPE  = ["Movie Genres","Movie Studios"]
TV_CHTYPE     = ["TV Networks","TV Genres","Mixed Genre"]

PRIMARY_BACKGROUND   = 'FF11375C'
SECONDARY_BACKGROUND = '334F4F9E'
DIALOG_TINT          = 'FF181B1E'
BUTTON_FOCUS         = 'FF2866A4'
SELECTED             = 'FF5BE5EE'
