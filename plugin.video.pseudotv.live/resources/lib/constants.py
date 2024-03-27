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

from kodi_six    import xbmc, xbmcaddon

#info
ADDON_ID            = 'plugin.video.pseudotv.live'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
LANGUAGE            = REAL_SETTINGS.getLocalizedString

#constants
OVERLAY_DELAY       = 15    #secs
DTFORMAT            = '%Y%m%d%H%M%S'
DTZFORMAT           = '%Y%m%d%H%M%S +%z'
DTJSONFORMAT        = '%Y-%m-%d %H:%M:%S'
LANG                = 'en' #todo parse kodi region settings
DEFAULT_ENCODING    = "utf-8"
PROMPT_DELAY        = 4000 #msecs
AUTOCLOSE_DELAY     = 8    #secs
RADIO_ITEM_LIMIT    = 250
CHANNEL_LIMIT       = 999
AUTOTUNE_LIMIT      = 3

AUTOTUNE_TYPES      = ["Playlists",
                       "TV Networks",
                       "TV Shows",
                       "TV Genres",
                       "Movie Genres",
                       "Movie Studios",
                       "Mixed Genres",
                       "Mixed",
                       "Recommended",
                       "Services",
                       "Music Genres"]

GROUP_TYPES         = ['Addon', 'Directory', 'TV', 'Movies', 'Music', 'Other', 'PVR', 'Plugin', 'Radio', 'Smartplaylist', 'UPNP', 'IPTV'] + AUTOTUNE_TYPES

VFS_TYPES           = ["plugin://",
                       "pvr://",
                       "upnp://",
                       "resource://"]
                       
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

VOD_URL             = 'plugin://{addon}/?mode=vod&title={title}&chid={chid}&vid={vid}.pvr'
TV_URL              = 'plugin://{addon}/?mode=tv&name={name}&chid={chid}.pvr'
RADIO_URL           = 'plugin://{addon}/?mode=radio&name={name}&chid={chid}&radio={radio}&vid={vid}.pvr'
LIVE_URL            = 'plugin://{addon}/?mode=live&name={name}&chid={chid}&vid={vid}&duration={duration}&start={start}.pvr'
BROADCAST_URL       = 'plugin://{addon}/?mode=broadcast&name={name}&chid={chid}&vid={vid}&duration={duration}&start={start}.pvr'
              
PTVL_REPO           = 'repository.pseudotv'
PVR_CLIENT_ID       = 'pvr.iptvsimple'
PVR_CLIENT_NAME     = xbmcaddon.Addon(id=PVR_CLIENT_ID).getAddonInfo('name')

#docs
README_FLE          = os.path.join(ADDON_PATH,'README.md')
WELCOME_FLE         = os.path.join(ADDON_PATH,'welcome.txt')
CHANGELOG_FLE       = os.path.join(ADDON_PATH,'changelog.txt')
LICENSE_FLE         = os.path.join(ADDON_PATH,'LICENSE')

#folders
IMAGE_LOC           = os.path.join(ADDON_PATH,'resources','images')
MEDIA_LOC           = os.path.join(ADDON_PATH,'resources','skins','default','media')
SFX_LOC             = os.path.join(MEDIA_LOC,'sfx')
BACKUP_LOC          = os.path.join(SETTINGS_LOC,'backup')
CACHE_LOC           = os.path.join(SETTINGS_LOC,'cache') #default User_Folder path

#files
XMLTVFLE            = '%s.xml'%('pseudotv')
M3UFLE              = '%s.m3u'%('pseudotv')
CHANNELFLE          = 'channels.json'
LIBRARYFLE          = 'library.json'
GENREFLE            = 'genres.xml'
TVGROUPFLE          = 'tv_groups.xml'
RADIOGROUPFLE       = 'radio_groups.xml'
PROVIDERFLE         = 'providers.xml'
CHANNELBACKUPFLE    = 'channels.backup'
CHANNELRESTOREFLE   = 'channels.restore'

VIDEO_EXTS          = xbmc.getSupportedMedia('video').split('|')
MUSIC_EXTS          = xbmc.getSupportedMedia('music').split('|')
IMAGE_EXTS          = xbmc.getSupportedMedia('picture').split('|')

#file paths
SETTINGS_FLE        = os.path.join(SETTINGS_LOC,'settings.xml')
CHANNELFLE_BACKUP   = os.path.join(BACKUP_LOC,CHANNELBACKUPFLE)
CHANNELFLE_RESTORE  = os.path.join(BACKUP_LOC,CHANNELRESTOREFLE)

#sfx
BING_WAV            = os.path.join(SFX_LOC,'bing.wav')
NOTE_WAV            = os.path.join(SFX_LOC,'notify.wav')

#remotes
IMPORT_ASSET        = os.path.join(ADDON_PATH,'remotes','asset.json')
RULEFLE_DEFAULT     = os.path.join(ADDON_PATH,'remotes','rule.json')
M3UFLE_DEFAULT      = os.path.join(ADDON_PATH,'remotes','m3u.json')
GROUPFLE_DEFAULT    = os.path.join(ADDON_PATH,'remotes','groups.xml')
LIBRARYFLE_DEFAULT  = os.path.join(ADDON_PATH,'remotes',LIBRARYFLE)
CHANNELFLE_DEFAULT  = os.path.join(ADDON_PATH,'remotes',CHANNELFLE)
GENREFLE_DEFAULT    = os.path.join(ADDON_PATH,'remotes',GENREFLE)
PROVIDERFLE_DEFAULT = os.path.join(ADDON_PATH,'remotes',PROVIDERFLE)

#images
LOGO                = os.path.join(MEDIA_LOC,'wlogo.png')
COLOR_LOGO          = os.path.join(ADDON_PATH,'resources','skins','default','media','logo.png')
HOST_LOGO           = 'http://github.com/PseudoTV/PseudoTV_Live/blob/master/plugin.video.pseudotv.live/resources/skins/default/media/logo.png?raw=true'

#rules
##builder
RULES_ACTION_CHANNEL_VERIFY              = 1 
RULES_ACTION_CHANNEL_START               = 2 
RULES_ACTION_CHANNEL_BUILD_START         = 3
RULES_ACTION_CHANNEL_BUILD_PATH          = 4
RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE  = 5
RULES_ACTION_CHANNEL_BUILD_FILELIST_POST = 6
RULES_ACTION_CHANNEL_BUILD_TIME_PRE      = 7
RULES_ACTION_CHANNEL_BUILD_TIME_POST     = 8
RULES_ACTION_CHANNEL_BUILD_STOP          = 9
RULES_ACTION_CHANNEL_STOP                = 10
##player
RULES_ACTION_PLAYBACK      = 11
RULES_ACTION_PLAYER_START  = 12
RULES_ACTION_PLAYER_CHANGE = 13
RULES_ACTION_PLAYER_STOP   = 14
##overlay/background
RULES_ACTION_OVERLAY_OPEN     = 21
RULES_ACTION_OVERLAY_CLOSE    = 22
RULES_ACTION_BACKGROUND_OPEN  = 23
RULES_ACTION_BACKGROUND_CLOSE = 24
