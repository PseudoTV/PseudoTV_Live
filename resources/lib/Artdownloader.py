#   Copyright (C) 2015 Kevin S. Graer
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

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, datetime, random
import threading
import sys, re
import random, traceback
import urllib, urllib2, urlparse
import socket

from apis.fanarttv import *
from apis.language import *
from ChannelList import *
from Globals import *
from FileAccess import FileAccess
from xml.etree import ElementTree as ET
from apis import tvdb
from apis import tmdb
from urllib import unquote, quote
from utils import *
from HTMLParser import HTMLParser

try:
    from metahandler import metahandlers
    metaget = metahandlers.MetaData(preparezip=False)
except Exception,e:  
    ENHANCED_DATA = False
    xbmc.log("script.pseudotv.live-Artdownloader: metahandler Import Failed" + str(e))   


try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
    
try:
    from PIL import Image
    from PIL import ImageEnhance
except:
    pass
    
socket.setdefaulttimeout(30)

class Artdownloader:

    def __init__(self):
        self.chanlist = ChannelList()
        self.fanarttv = fanarttv()
        self.tvdbAPI = tvdb.TVDB()
        self.tmdbAPI = tmdb.TMDB()  
        
        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Artdownloader: ' + msg, level)


    def getFallback_Arttype(self, arttype):
        arttype = arttype.lower()
        arttype = arttype.replace('landscape','fanart')
        arttype = arttype.replace('folder','poster')
        arttype = arttype.replace('thumb','poster')
        # arttype = arttype.replace('fanart','landscape')
        # arttype = arttype.replace('clearlogo','clearart')
        arttype = arttype.replace('clearart','clearlogo')
        arttype = arttype.replace('character','clearlogo')
        self.log("getFallback_Arttype = " + arttype)
        return arttype

        
    def dbidArt(self, type, chname, mpath, dbid, arttypeEXT):
        self.log("dbidArt")
        file_detail = []
        try:
            if type == 'tvshow':
                json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShowDetails","params":{"tvshowid":%s,"properties":["art","thumbnail","fanart"]},"id":1}' % dbid)
            elif type == 'movie':
                json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovieDetails","params":{"movieid":%s,"properties":["art","thumbnail","fanart"]},"id":1}' % dbid)
            else:
                return 'NA.png'
            arttype = (arttypeEXT.split(".")[0])
            json_folder_detail = self.chanlist.sendJSON(json_query)
            file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
            return self.searchDetails(file_detail, arttype)
        except Exception,e:  
            self.log("dbidArt, Failed" + str(e), xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)
        
        
    def JsonArt(self, type, chname, mpath, arttypeEXT):
        self.log("JsonArt")
        file_detail = []
        try:
            json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","media":"video","properties":["art","fanart","thumbnail"]}, "id": 1}' % (mpath))
            arttype = (arttypeEXT.split(".")[0])
            json_folder_detail = self.chanlist.sendJSON(json_query)
            file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
            return self.searchDetails(file_detail, arttype)
        except Exception,e:  
            self.log("JsonArt, Failed" + str(e), xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)


    def searchDetails(self, file_detail, arttype):
        self.log("searchDetails")
        for f in file_detail:
            try:
                arttypes = re.search(('"%s" *: *"(.*?)"' % arttype), f)
                arttypes_fallback = re.search(('"%s" *: *"(.*?)"' % self.getFallback_Arttype(arttype)), f)
                if arttypes != None and len(arttypes.group(1)) > 0:
                    return (unquote(xbmc.translatePath((arttypes.group(1).split(','))[0]))).replace('image://','').replace('.jpg/','.jpg').replace('.png/','.png') 
                elif arttypes_fallback != None and len(arttypes_fallback.group(1)) > 0:
                    if (arttypes_fallback.group(1)).lower() ==  (self.getFallback_Arttype(arttype)).lower():
                        return (unquote(xbmc.translatePath((arttypes_fallback.group(1).split(','))[0]))).replace('image://','').replace('.jpg/','.jpg').replace('.png/','.png')
            except Exception,e:  
                self.log("searchDetails, Failed" + str(e), xbmc.LOGERROR)
        return 'NA.png'
                
    
    def FindArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, arttypeEXT):
        self.log("FindArtwork")
        try:
            setImage = 'NA.png'
            CacheArt = False
            DefaultArt = False
            arttypeEXT = EXTtype(arttypeEXT)
            arttype = arttypeEXT.split(".")[0]
            fle = id + '-' + arttypeEXT
            ext = arttypeEXT.split('.')[1]
            cachedthumb = xbmc.getCacheThumbName(os.path.join(removeNonAscii(mpath), fle))
            cachefile = xbmc.translatePath(os.path.join(ART_LOC, cachedthumb[0], cachedthumb[:-4] + "." + ext)).replace("\\", "/")
            kodifile = xbmc.translatePath(os.path.join('special://masterprofile/Thumbnails', cachedthumb[0], cachedthumb[:-4] + "." + ext)).replace("\\", "/")
            
            if isLowPower() == True:
                return setImage
            
            elif id != '0':
                if FileAccess.exists(cachefile):
                    self.log('FindArtwork, Using Cache')
                    return cachefile   
                
                elif FileAccess.exists(kodifile):
                    self.log('FindArtwork, Using Kodi Cache')
                    return kodifile   
                
            if chtype <= 7 or chtype == 12:
                self.log('FindArtwork, chtype <= 7 - Local Art')
                smpath = mpath.rsplit('/',2)[0]
                artSeries = xbmc.translatePath(os.path.join(smpath, arttypeEXT))
                artSeason = xbmc.translatePath(os.path.join(mpath, arttypeEXT))
                artSeries_fallback = xbmc.translatePath(os.path.join(smpath, self.getFallback_Arttype(arttypeEXT)))
                artSeason_fallback = xbmc.translatePath(os.path.join(mpath, self.getFallback_Arttype(arttypeEXT)))

                if type == 'tvshow': 
                    if FileAccess.exists(artSeries):
                        return artSeries
                    elif FileAccess.exists(artSeason):
                        return artSeason
                    elif FileAccess.exists(artSeries_fallback): 
                        return artSeries_fallback
                    elif FileAccess.exists(artSeason_fallback):
                        return artSeason_fallback    
                elif type == 'movie':
                    if FileAccess.exists(artSeason):
                        return artSeason
                    elif FileAccess.exists(artSeason_fallback):
                        return artSeason_fallback    
            
                SetImage = self.JsonArt(type, chname, mpath, arttypeEXT)
                if FileAccess.exists(SetImage):
                    return SetImage
                elif dbid != '0':
                    SetImage = self.dbidArt(type, chname, mpath, dbid, arttypeEXT)
                    if FileAccess.exists(SetImage):
                        return SetImage
                SetImage = self.DownloadMissingArt(type, title, year, id, arttype, cachefile, chname, mpath, arttypeEXT)
                if FileAccess.exists(SetImage):
                    return SetImage
            else:
                if id == '0':
                    if (type == 'youtube' or mpath.startswith(self.chanlist.youtube_player)) and dbid != '0':
                        self.log('FindArtwork, YOUTUBE')
                        return "http://i.ytimg.com/vi/"+dbid+"/mqdefault.jpg"
                    elif type == 'rss' and dbid != '0':
                        self.log('FindArtwork, RSS')
                        return decodeString(dbid)
                    elif chtype in [8] and dbid != '0':
                        self.log('FindArtwork, decode dbid')
                        return decodeString(dbid)
                else:
                    SetImage = self.DownloadMissingArt(type, title, year, id, arttype, cachefile, chname, mpath, arttypeEXT)
                    if FileAccess.exists(SetImage):
                        return SetImage
                    elif dbid != '0':
                        self.log('FindArtwork, decode dbid')
                        return decodeString(dbid)
            return 'NA.png'
        except Exception,e:  
            self.log("script.pseudotv.live-Artdownloader: FindArtwork Failed" + str(e), xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR) 
                
              
    def dbidDecode(self, dbid, cachefile):
        self.log('dbidDecode')
        url = decodeString(dbid)
        if url.startswith('http'):
            download_silent(url,cachefile)
            return cachefile
        else:
            return 'NA.png'
              
              
    def SetDefaultArt(self, chname, mpath, arttypeEXT):
        self.log('SetDefaultArt')
        try:
            setImage = ''
            arttype = arttypeEXT.split(".")[0]
            MediaImage = os.path.join(MEDIA_LOC, (arttype + '.png'))
            StockImage = os.path.join(IMAGES_LOC, (arttype + '.png'))
            ChannelLogo = os.path.join(LOGO_LOC,chname[0:18] + '.png')

            # Channel Logo
            if FileAccess.exists(ChannelLogo) == True:
                return ChannelLogo
            # Plugin Icon
            elif mpath[0:6] == 'plugin':
                icon = 'special://home/addons/'+(mpath.replace('plugin://',''))+ '/icon.png'
                return icon
            # Selected Skin Fallback ie (poster.jpg, landscape.jpg, logo.png, etc...)
            elif FileAccess.exists(MediaImage) == True:
                return MediaImage
            # Default Skin Fallback ie (poster.jpg, landscape.jpg, logo.png, etc...)
            elif FileAccess.exists(StockImage) == True:
                return StockImage
            # PTVL Icon
            else:
                return THUMB
        except Exception,e:  
            self.log("script.pseudotv.live-Artdownloader: SetDefaultArt Failed" + str(e), xbmc.LOGERROR)
            return THUMB


    def DownloadMissingArt(self, type, title, year, id, arttype, cachefile, chname, mpath, arttypeEXT):
        self.log('DownloadMissingArt')
        url = ''
        if ENHANCED_DATA == True and id != '0':  
            url = self.findMissingArt(type, id, arttype, cachefile, chname, mpath, arttypeEXT)
            if not url.startswith('http'):
                # search fallback artwork
                url = self.findMissingArt(type, id, self.getFallback_Arttype(arttype), cachefile, chname, mpath, self.getFallback_Arttype(arttype))
        
        if not url.startswith('http'):
            # search metahanlder artwork
            url = self.findMissingArtMeta(type, title, year, arttype)
        
        if url.startswith('http'):
            download_silent(url,cachefile)
            return cachefile
        else:
            return 'NA.png'
           
           
    def findMissingArtMeta(self, type, title, year, arttype):
        self.log('findMissingArtMeta')
        url = ''
        try:
            meta = metaget.get_meta(type, title, str(year)) 
            if arttype in ['thumb','poster']:
                url = meta['cover_url']
            elif arttype in ['fanart','landscape']:
                url = meta['backdrop_url']  
            elif arttype in ['banner']:
                url = meta['banner_url']
        except:
            pass
        if url.startswith('http'):
            return url
        else:
            return 'NA.png'
           
           
    def findMissingArt(self, type, id, arttype, cachefile, chname, mpath, arttypeEXT):
        url = ''
        drive, Dpath = os.path.splitdrive(cachefile)
        path, filename = os.path.split(Dpath)
        
        if FileAccess.exists(os.path.join(drive,path)) == False:
            FileAccess.makedirs(os.path.join(drive,path))   
                    
        if type == 'tvshow':
            self.log('findMissingArt, tvshow')
            tvdb_Types = ['banner', 'fanart', 'folder', 'poster']
                
            if arttype in tvdb_Types:
                # correct database naming schema
                arttype = arttype.replace('banner', 'graphical').replace('folder', 'poster')
                url = self.findTVDBArt(type, id, arttype, arttypeEXT)
            if not url.startswith('http'):
                # correct database naming schema
                arttype = arttype.replace('graphical', 'banner').replace('folder', 'poster')
                url = self.findFANTVArt(type, id, arttype, arttypeEXT)

        elif type == 'movie':
            self.log('findMissingArt, movie')
            tmdb_Types = ['banner', 'fanart', 'folder', 'poster']

            if arttype in tmdb_Types:
                # correct database naming schema
                arttype = arttype.replace('folder', 'poster')
                url = self.findTMDBArt(type, id, arttype, arttypeEXT)
            if not url.startswith('http'):
                # correct database naming schema
                arttype = arttype.replace('folder', 'poster')
                url = self.findFANTVArt(type, id, arttype, arttypeEXT)

        # todo music artwork support
        # todo google image search, obdb, metahandler search
        if url.startswith('http'):
            return url
        else:
            return 'NA.png'
 
 
    def findTVDBArt(self, type, id, arttype, arttypeEXT):
        self.log('findTVDBArt')
        url = ''
        tvdb = str(self.tvdbAPI.getBannerByID(id, arttype))
        tvdbPath = tvdb.split(', ')[0].replace("[('", "").replace("'", "") 
        if tvdbPath.startswith('http'):
            url = tvdbPath
        return url
        
        
    def findTMDBArt(self, type, id, arttype, arttypeEXT):
        self.log('findTMDBArt')
        url = ''
        tmdb = self.tmdbAPI.get_image_list(id)
        # todo replace lazy code with regex parsing
        data = str(tmdb).replace("[", "").replace("]", "").replace("'", "")
        data = data.split('}, {')
        tmdbPath = str([s for s in data if arttype in s]).split("', 'width: ")[0]
        match = re.search('url *: *(.*?),', tmdbPath)
        if match:
            tmdbPath = match.group().replace(",", "").replace("url: u", "").replace("url: ", "")
            if tmdbPath.startswith('http'):
                url = tmdbPath
        return url

                
    def findFANTVArt(self, type, id, arttype, arttypeEXT):
        self.log('findFANTVArt')
        url = ''
        fanPath = ''
        if type == 'tvshow':
            fan = str(self.fanarttv.get_image_list_TV(id))
        elif type == 'movie':
            fan = str(self.fanarttv.get_image_list_Movie(id))

        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(fan)
        pref_language = get_abbrev(REAL_SETTINGS.getSetting('limit_preferred_language'))
        
        for f in file_detail:
            try:
                languages = re.search("'language' *: *(.*?),", f)
                art_types = re.search("'art_type' *: *(.*?),", f)
                fanPaths = re.search("'url' *: *(.*?),", f)       
                if languages and len(languages.group(1)) > 0:
                    language = (languages.group(1)).replace("u'",'').replace("'",'')
                    if language.lower() == pref_language.lower():
                        if art_types and len(art_types.group(1)) > 0:
                            art_type = art_types.group(1).replace("u'",'').replace("'",'').replace("[",'').replace("]",'')
                            if art_type.lower() == arttype.lower():
                                if fanPaths and len(fanPaths.group(1)) > 0:
                                    fanPath = fanPaths.group(1).replace("u'",'').replace("'",'')
                                    if fanPath.startswith('http'):
                                        url = fanPath
            except:
                pass                                                                     
        return url


    def AlphaLogo(self, org, mod):
        self.log("AlphaLogo")
        try:
            img = Image.open(org)
            img = img.convert("RGBA")
            datas = img.getdata()
            newData = []
            for item in datas:
                if item[0] == 255 and item[1] == 255 and item[2] == 255:
                    newData.append((255, 255, 255, 0))
                else:
                    newData.append(item)
            img.putdata(newData)
            img.save(mod, "PNG")
        except Exception,e:  
            self.log("AlphaLogo" + str(e), xbmc.LOGERROR)

            
    def ConvertBug(self, org, mod):
        self.log("ConvertBug")
        try:
            drive, path = os.path.splitdrive(mod)
            path, filename = os.path.split(path)
            if FileAccess.exists(path) == False:
                FileAccess.makedirs(path)
                
            org =  xbmc.translatePath(org)
            original = Image.open(org)                  
            converted_img = original.convert('LA')  
            img_bright = ImageEnhance.Brightness(converted_img)
            converted_img = img_bright.enhance(1.0)     
            converted_img.save(mod)
            return mod
        except Exception,e:  
            self.log("ConvertBug, Failed " + str(e), xbmc.LOGERROR)
            return org
            
        
    def getDefaultBug(self, chname):     
        self.log("getDefaultBug")       
        if REAL_SETTINGS.getSetting('UNAlter_ChanBug') == 'true':
            DefaultBug = os.path.join(IMAGES_LOC,'logo.png')
            if chname == 'OnDemand':
                DefaultBug = os.path.join(IMAGES_LOC,'ondemand.png')
        else:
            DefaultBug = os.path.join(IMAGES_LOC,'Default.png')
            if chname == 'OnDemand':
                DefaultBug = os.path.join(IMAGES_LOC,'Default_ondemand.png')
        return DefaultBug
        
        
    def FindBug(self, chtype, chname):
        self.log("FindBug, chname = " + chname)
        try:
            setImage = ''
            BugName = (chname[0:18] + '.png')
            BugFLE = xbmc.translatePath(os.path.join(LOGO_LOC,BugName))
            cachedthumb = xbmc.getCacheThumbName(BugFLE)
            cachefile = xbmc.translatePath(os.path.join(ART_LOC, cachedthumb[0], cachedthumb[:-4] + ".png")).replace("\\", "/")
            DefaultBug = self.getDefaultBug(chname)
            
            # no channel bug for livetv/internettv
            if chtype in [8,9]:
                return 'NA.png' 
            else:
                if REAL_SETTINGS.getSetting('UNAlter_ChanBug') == 'true':
                    if FileAccess.exists(BugFLE) == False:
                        BugFLE = DefaultBug
                    return BugFLE
                else:
                    if FileAccess.exists(cachefile) == True:
                        return cachefile
                    elif FileAccess.exists(BugFLE) == False:
                        return DefaultBug
                    return self.ConvertBug(BugFLE, cachefile)
        except Exception,e:  
            self.log("FindBug, Failed" + str(e), xbmc.LOGERROR)
            return 'NA.png'