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

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import subprocess, os
import time, datetime, random
import threading
import sys, re
import random, traceback
import urllib, urllib2, urlparse, requests
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
from BeautifulSoup import BeautifulSoup
from FileAccess import FileAccess

try:
    from metahandler import metahandlers
    metaget = metahandlers.MetaData(preparezip=False, tmdb_api_key=TMDB_API_KEY)
    ENHANCED_DATA = True
except Exception,e:
    ENHANCED_DATA = False
    xbmc.log("script.pseudotv.live-Artdownloader: metahandler Import Failed" + str(e))   

try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
    
try:
    from PIL import Image, ImageEnhance
except:
    if int(REAL_SETTINGS.getSetting('Enable_ChannelBug')) == 2:
        REAL_SETTINGS.setSetting("Enable_ChannelBug","1")
        
socket.setdefaulttimeout(5)

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

        
    def FolderArt(self, type, chname, mpath, arttypeEXT):
        self.log("FolderArt, arttypeEXT = " + arttypeEXT)
        file_detail = []
        try:
            json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","media":"pictures","properties":[]},"id":1}' % (mpath))
            json_folder_detail = self.chanlist.sendJSON(json_query)
            file_detail = re.compile("{(.*?)}", re.DOTALL ).findall(json_folder_detail)
            
            for f in file_detail:
                files = re.search('"file" *: *"(.*?)",', f)
                if files:
                    labels = re.search('"label" *: *"(.*?)",', f)
                    if len(labels.group(1)) > 0:
                        if (labels.group(1)).lower() == arttypeEXT.lower():
                            return (files.group(1).replace("\\\\", "\\"))
            return 'NA.png'
        except Exception,e:  
            self.log("FolderArt, Failed" + str(e), xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)
            return 'NA.png'
            
                
    def searchDetails(self, json_folder_detail, arttypeEXT):
        print json_folder_detail, arttypeEXT
        arttype = (arttypeEXT.split(".")[0])
        file_detail = re.compile("{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        for f in file_detail:
            arttypes = re.search(('"%s" *: *"(.*?)"' % arttype), f)
            arttypes_fallback = re.search(('"%s" *: *"(.*?)"' % self.getFallback_Arttype(arttype)), f)
            if arttypes != None and len(arttypes.group(1)) > 0:
                return (unquote(xbmc.translatePath((arttypes.group(1).split(','))[0]))).replace('image://','').replace('.jpg/','.jpg').replace('.png/','.png') 
            elif arttypes_fallback != None and len(arttypes_fallback.group(1)) > 0:
                if (arttypes_fallback.group(1)).lower() ==  (self.getFallback_Arttype(arttype)).lower():
                    return (unquote(xbmc.translatePath((arttypes_fallback.group(1).split(','))[0]))).replace('image://','').replace('.jpg/','.jpg').replace('.png/','.png')
        return 'NA.png'

            
    def dbidArt(self, type, chname, dbid, arttypeEXT):
        if dbid == '0':
            return 'NA.png'
        self.log("dbidArt")
        file_detail = []
        try:
            if type in ['tvshow','episode']:
                json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShowDetails","params":{"tvshowid":%s,"properties":["art"]},"id":1}' % dbid)
            elif type == 'movie':
                json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovieDetails","params":{"movieid":%s,"properties":["art"]},"id":1}' % dbid)
            else:
                #todo music support
                return 'NA.png'
            arttype = (arttypeEXT.split(".")[0])
            json_folder_detail = self.chanlist.sendJSON(json_query)
            return self.searchDetails(json_folder_detail, arttypeEXT)
        except Exception,e:  
            self.log("dbidArt, Failed" + str(e), xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)
            return 'NA.png'
        
            
    def TitleArt(self, type, chname, title, arttypeEXT):
        self.log("TitleArt")
        file_detail = []
        title = urllib.quote_plus(title)
        try:
            if type in ['tvshow','episode']:
                json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTvShows","params":{"filter":{"field":"title","operator":"is","value":"%s"},"properties":["art"]},"id":1}' % title)
            elif type == 'movie':
                json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{"filter":{"field":"title","operator":"is","value":"%s"},"properties":["art"]},"id":1}' % title)
            else:
                json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary","filter": {"operator":"is", "field":"title", "value":"%s"},"properties":["art"]},"id":1}' % title)
            arttype = (arttypeEXT.split(".")[0])
            json_folder_detail = self.chanlist.sendJSON(json_query)
            return self.searchDetails(json_folder_detail, arttypeEXT)
        except Exception,e:  
            self.log("TitleArt, Failed" + str(e), xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)
            return 'NA.png'


    def FindArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, arttypeEXT, fallback=False):
        self.log('FindArtwork, chtype = ' + str(chtype) + ', id = ' + str(id) +  ', dbid = ' + str(dbid) + ', arttypeEXT = ' + arttypeEXT)
        try:
            setImage = 'NA.png'
            SetDefault = self.SetDefaultArt(chname, mpath, arttypeEXT)
            
            if isLowPower() == True:
                return SetDefault
                
            # local media
            if chtype <= 7 or chtype == 12:
                if type in ['tvshow','episode']:
                    self.log('FindArtwork, Local TVShow Folder')
                    smpath = mpath.rsplit('/',2)[0]
                    setImage = self.FolderArt(type, chname, smpath, arttypeEXT)
                    if FileAccess.exists(setImage):
                        return setImage
                    
                self.log('FindArtwork, Local Season Folder')
                setImage = self.FolderArt(type, chname, mpath, arttypeEXT)
                if FileAccess.exists(setImage):
                    return setImage
                                    
                self.log('FindArtwork, Local DBID Lookup')
                setImage = self.dbidArt(type, chname, dbid, arttypeEXT)
                if FileAccess.exists(setImage):
                    return setImage
                        
            self.log('FindArtwork, Local Title Lookup')
            setImage = self.TitleArt(type, chname, title, arttypeEXT)
            if FileAccess.exists(setImage):
                return setImage
                  
            self.log('FindArtwork, Online Lookup')
            setImage = self.LookupMissingArtwork(type, title, year, id, (arttypeEXT.split(".")[0]), chname, mpath, arttypeEXT)
            if setImage.startswith('http'):
                return setImage
                
            if fallback == False:
                fallback = True
                self.log('FindArtwork, Checking Fallback')
                setImage = self.FindArtwork(type, title, year, chtype, chname, id, dbid, mpath, self.getFallback_Arttype(arttypeEXT), fallback)
                if FileAccess.exists(setImage):
                    return setImage

            if (type == 'youtube' or mpath.startswith(self.chanlist.youtube_player)) and dbid != '0':
                self.log('FindArtwork, Youtube Lookup')
                return "http://i.ytimg.com/vi/"+dbid+"/mqdefault.jpg"
            
            if chtype in [8,11] and dbid != '0':
                self.log('FindArtwork, Decode thumb')
                return self.dbidDecode(dbid)      
   
            if chtype == 8 and dbid == '0':
                setImage = self.findMissingArtLive(title)
                if setImage.startswith('http'):
                    return setImage
                    
            self.log('FindArtwork, Using Default Art')
            return SetDefault
        except Exception,e:  
            self.log("script.pseudotv.live-Artdownloader: FindArtwork Failed! " + str(e), xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR) 
            return THUMB
                

    def dbidDecode(self, dbid):
        self.log('dbidDecode')
        return decodeString(dbid)
              
              
    def SetDefaultArt(self, chname, mpath, arttypeEXT):
        self.log('SetDefaultArt')
        try:
            setImage = ''
            arttype = arttypeEXT.split(".")[0]
            MediaImage = os.path.join(MEDIA_LOC, (arttype + '.png'))
            StockImage = os.path.join(IMAGES_LOC, (arttype + '.png'))
            ChannelLogo = os.path.join(LOGO_LOC,chname + '.png')
            
            # Selected Skin Fallback ie (poster.jpg, landscape.jpg, logo.png, etc...)
            if FileAccess.exists(MediaImage) == True:
                self.log('SetDefaultArt, return MediaImage')
                return MediaImage
            # Channel Logo
            elif FileAccess.exists(ChannelLogo) == True:
                self.log('SetDefaultArt, return ChannelLogo')
                return ChannelLogo
            # Plugin Icon
            elif mpath[0:6] == 'plugin':
                icon = 'special://home/addons/'+(mpath.replace('plugin://',''))+ '/icon.png'
                self.log('SetDefaultArt, return plugin icon')
                return icon
            # Default Skin Fallback ie (poster.jpg, landscape.jpg, logo.png, etc...)
            elif FileAccess.exists(StockImage) == True:
                self.log('SetDefaultArt, return StockImage')
                return StockImage
            # PTVL Icon
            else:
                self.log('SetDefaultArt, return THUMB')
                return THUMB
        except Exception,e:  
            self.log("script.pseudotv.live-Artdownloader: SetDefaultArt Failed" + str(e), xbmc.LOGERROR)
            return THUMB

            
    def LookupMissingArtwork(self, type, title, year, id, arttype, chname, mpath, arttypeEXT):
        self.log('LookupMissingArtwork')
        url = '' 
        if id != '0' and isLowPower() == False:  
            url = self.findMissingArt(type, id, arttype, chname, mpath, arttypeEXT)                
            if url.startswith('http'):
                return url
        return 'NA.png'
          

    def findMissingArtLive(self, title):
        self.log('findMissingArtLive, title = ' + title)
        if len(title) > 0 and isLowPower() == False:
            url = ''
            request = self.getGoogleImages('"%s"+site:zap2it.com' %title)
            for image in request:
                image = image.split('?')[0]
                image = image.split('.jpg%')[0]+'.jpg'
                if image.endswith(('png','jpg')):
                    if 'tribzap2it' and 'l_h12_aa' in image:
                        url = image
                    elif 'images.zap2it.com' and 'b_h12_ab' in image:
                        url = image
                    elif 'images.zap2it.com' and 'l_h6_aa' in image:
                        url = image
                    elif 'images.zap2it.com' and 'b_h6_ab' in image:
                        url = image   
                    if url.startswith('http'):
                        return url
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
        return 'NA.png'
           
           
    def findMissingArt(self, type, id, arttype, chname, mpath, arttypeEXT):
        url = ''     
        if type in ['tvshow','episode']:
            self.log('findMissingArt, tvshow')
            if arttype in ['banner', 'fanart', 'folder', 'poster']:
                arttype = arttype.replace('banner', 'graphical').replace('folder', 'poster')
                url = self.findTVDBArt(type, id, arttype, arttypeEXT)
                if url.startswith('http'):
                    return url
            arttype = arttype.replace('graphical', 'banner').replace('folder', 'poster')
            url = self.findFANTVArt(type, id, arttype, arttypeEXT)
            if url.startswith('http'):
                return url

        elif type == 'movie':
            self.log('findMissingArt, movie')
            if arttype in ['banner', 'fanart', 'folder', 'poster']:
                arttype = arttype.replace('folder', 'poster')
                url = self.findTMDBArt(type, id, arttype, arttypeEXT)
                if url.startswith('http'):
                    return url
            arttype = arttype.replace('folder', 'poster')
            url = self.findFANTVArt(type, id, arttype, arttypeEXT)
            if url.startswith('http'):
                return url
        return 'NA.png'
 
 
    def findTVDBArt(self, type, id, arttype, arttypeEXT):
        self.log('findTVDBArt')
        url = ''
        tvdb = str(self.tvdbAPI.getBannerByID(id, arttype))
        tvdbPath = tvdb.split(', ')[0].replace("[('", "").replace("'", "") 
        if tvdbPath.startswith('http'):
            return tvdbPath
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
                return tmdbPath
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
        
    # Adapted from https://github.com/marcelveldt/script.skin.helper.service/blob/master/resources/lib/ArtworkUtils.py#L712
    def getGoogleImages(self, terms, **kwargs):
        start = ''
        page = 1
        args = ['q={0}'.format(urllib.quote_plus(uni(terms)))]
        for k in kwargs.keys():
            if kwargs[k]: args.append('{0}={1}'.format(k,kwargs[k]))
        query = '&'.join(args)
        start = ''
        baseURL = 'http://www.google.com/search?site=imghp&tbm=isch&tbs=isz:m{start}{query}'
        url = baseURL.format(start=start,query='&' + query)
        self.log("getGoogleImages, url = " + url)
        html = requests.get(url, headers={'User-agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows Phone OS 7.0; Trident/3.1; IEMobile/7.0; LG; GW910)'}, timeout=5).text
        soup = BeautifulSoup(html)
        results = []
        for div in soup.findAll('div'):
            if div.get("id") == "images":
                for a in div.findAll("a"):
                    page = a.get("href")
                    try:
                        img = page.split("imgurl=")[-1]
                        img = img.split("&imgrefurl=")[0]
                        results.append(img)
                    except: pass
        return results

        
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
            return os.path.join(IMAGES_LOC,'icon_mono.png')
            
        
    def FindBug(self, chtype, chname):
        self.log("FindBug, chname = " + chname)
        try:
            FindBug_Type = int(REAL_SETTINGS.getSetting('Enable_ChannelBug'))
            
            OEMBugFLE_ANI = xbmc.translatePath(os.path.join(LOGO_LOC,(chname + '.gif')))
            OEMBugFLE = xbmc.translatePath(os.path.join(LOGO_LOC,(chname + '.png')))
            NEWBugFLE = xbmc.translatePath(os.path.join(LOGO_LOC,(chname + '_mono.png')))

            OEMDefaultBugFLE = os.path.join(IMAGES_LOC,'logo.png')
            NEWDefaultBugFLE = os.path.join(IMAGES_LOC,'icon_mono.png')
                                
            # no channel bug for livetv/internettv
            if chtype in [8,9]:
                return 'NA.png' 

            if FindBug_Type > 0:
                if FindBug_Type == 3:
                    if FileAccess.exists(OEMBugFLE_ANI) == True:
                        return OEMBugFLE_ANI
                if FindBug_Type == 2:
                    if FileAccess.exists(NEWBugFLE) == True:
                        return NEWBugFLE
                    if FileAccess.exists(NEWBugFLE) == False and FileAccess.exists(OEMBugFLE) == True:
                        return self.ConvertBug(OEMBugFLE, NEWBugFLE)
                    return NEWDefaultBugFLE
                if FileAccess.exists(OEMBugFLE) == True:
                    return OEMBugFLE
                return OEMDefaultBugFLE
        except Exception,e:  
            self.log("FindBug, Failed" + str(e), xbmc.LOGERROR)
            return 'NA.png'