#   Copyright (C) 2020 Lunatixz
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

import os, sys, re, platform, subprocess, struct, shutil, traceback, threading
import datetime, time, _strptime, base64, binascii, random, hashlib, difflib
import json, codecs, types, collections, six

from kodi_six              import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from itertools             import repeat, cycle, chain, zip_longest
from six.moves             import urllib
from contextlib            import contextmanager
from simplecache           import use_cache, SimpleCache
from xml.dom.minidom       import parse, parseString, Document
from xml.etree.ElementTree import ElementTree, Element, SubElement, tostring
from queue                 import Queue

try:
    from multiprocessing import cpu_count 
    from multiprocessing.pool import ThreadPool 
    ENABLE_POOL = True
    CORES = cpu_count()
except: ENABLE_POOL = False
    
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if PY3: 
    basestring = str
    unicode = str
    
# Plugin Info
ADDON_ID       = 'plugin.video.pseudotv.live'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

PVR_CLIENT     = 'pvr.iptvsimple'
USER_LOC       = (REAL_SETTINGS.getSetting('User_Folder') or SETTINGS_LOC)
XMLTVFLE       = os.path.join(USER_LOC,'%s.xml'%('pseudotv'))
M3UFLE         = os.path.join(USER_LOC,'%s.m3u'%('pseudotv'))
LOGO_LOC       = os.path.join(USER_LOC,'logos')
LOCK_LOC       = SETTINGS_LOC

CHANNELFLE     = os.path.join(SETTINGS_LOC,'channels.json')
CHANNELFLE_DEFAULT = os.path.join(ADDON_PATH,'channels.json')

GENREFLE         = os.path.join(USER_LOC,'genres.xml')
GENREFLE_DEFAULT = os.path.join(ADDON_PATH,'genres.xml')

VIDEO_EXTS     = xbmc.getSupportedMedia('video')
MUSIC_EXTS     = xbmc.getSupportedMedia('music')
IMAGE_EXTS     = xbmc.getSupportedMedia('picture')

DTFORMAT       = '%Y%m%d%H%M%S'
EPG_HRS        = 10800  # 3hr in seconds, Min. EPG guidedata
CHANNEL_LIMIT  = 999
CHANNEL_RANGE  = range(CHANNEL_LIMIT+1,(CHANNEL_LIMIT*4)) # pre-defined channel range. internal use.

ART_PARAMS        = ["thumb","logo","poster","fanart","banner","landscape","clearart","clearlogo"]
JSON_FILE_ENUM    = ["title","artist","albumartist","genre","year","rating","album","track","duration","comment","lyrics","musicbrainztrackid","musicbrainzartistid","musicbrainzalbumid","musicbrainzalbumartistid","playcount","fanart","director","trailer","tagline","plot","plotoutline","originaltitle","lastplayed","writer","studio","mpaa","cast","country","imdbnumber","premiered","productioncode","runtime","set","showlink","streamdetails","top250","votes","firstaired","season","episode","showtitle","thumbnail","file","resume","artistid","albumid","tvshowid","setid","watchedepisodes","disc","tag","art","genreid","displayartist","albumartistid","description","theme","mood","style","albumlabel","sorttitle","episodeguide","uniqueid","dateadded","size","lastmodified","mimetype","specialsortseason","specialsortepisode","sortartist","musicbrainzreleasegroupid","isboxset","totaldiscs","disctitle","releasedate","originaldate","bpm","bitrate","samplerate","channels","datemodified","datenew","customproperties"]
JSON_METHOD       = ["none","label","date","size","file","path","drivetype","title","track","time","artist","album","albumtype","genre","country","year","rating","votes","top250","programcount","playlist","episode","season","totalepisodes","watchedepisodes","tvshowstatus","showtitle","tvshowtitle","sorttitle","productioncode","mpaa","studio","dateadded","lastplayed","playcount","listeners","bitrate","random"] 
JSON_ORDER        = ['ascending','descending']
JSON_OPERATORS    = ["contains","doesnotcontain","is","isnot","startswith","endswith","greaterthan","lessthan","true","false"]
JSON_RETURN_TYPES = {'album':str,'albumartist':list,'albumartistid':list,'albumid':int,'albumlabel':str,'album':str,'albumstatus':str,'bitrate':int,'bpm':int,'cast':list,'channels':int,'comment':str,'compilation':bool,'contributors':str,'country':list,'customproperties':dict,'description':str,'disc':int,'disctitle':str,'displaycomposer':str,'displayconductor':str,'displaylyricist':str,'displayorchestra':str,'duration':int,'dynpath':str,'episode':int,'episodeguide':str,'firstaired':str,'id':int,'imdbnumber':str,'isboxset':bool,'lyrics':str,'mediapath':str,'mood':list,'mpaa':str,'musicbrainzartistid':list,'musicbrainztrackid':str,'originaldate':str,'originaltitle':str,'plotoutline':str,'premiered':str,'productioncode':str,'releasedate':str,'album':str,'samplerate':int,'season':int,'set':str,'setid':int,'showlink':list,'showtitle':str,'sorttitle':str,'specialsortepisode':int,'specialsortseason':int,'stu]dio':list,'style':list,'tag':list,'tagline':str,'theme':list,'top250':int,'totaldiscs':int,'track':int,'trailer':str,'tvshowid':int,'type':str,'uniqueid':int,'votes':str,'watchedepisodes':int,'writer':list}
LISTITEM_TYPES    = {'genre': (str,list),'country': (str,list),'year': int,'episode': int,'season': int,'sortepisode': int,'sortseason': int,'episodeguide': str,'showlink': (str,list),'top250': int,'setid': int,'tracknumber': int,'rating': float,'userrating': int,'playcount': int,'overlay': int,'cast': list,'castandrole': list,'director': (str,list),'mpaa': str,'plot': str,'plotoutline': str,'title': str,'originaltitle': str,'sorttitle': str,'duration': int,'studio': (str,list),'tagline': str,'writer': (str,list),'tvshowtitle': str,'premiered': str,'status': str,'set': str,'setoverview': str,'tag': (str,list),'imdbnumber': str,'code': str,'aired': str,'credits': (str,list),'lastplayed': str,'album': str,'artist': list,'votes': str,'path': str,'trailer': str,'dateadded': str,'mediatype': str,'dbid': int}

IMAGE_LOC      = os.path.join(ADDON_PATH,'resources','skins','default','media')
USE_COLOR      = REAL_SETTINGS.getSetting('Use_Color_Logos') == 'true'
IMAGE          = 'logo.png' if USE_COLOR else 'wlogo.png'
LOGO           = os.path.join(IMAGE_LOC,IMAGE)
LANG           = 'en' #todo

CHAN_TYPES     = ['TV_Shows','TV_Networks','TV_Genres','MOVIE_Genres','MIXED_Genres','MOVIE_Studios','MIXED_Other','MUSIC_Genres'] 
OVERLAY_FLE    = "%s.overlay.xml"%(ADDON_ID)
BCT_TYPES      = ['bumper','commercial','trailer','rating']
PRE_ROLL       = ['bumper','rating']
POST_ROLL      = ['commercial','trailer']

# Maximum is 10 for this
RULES_PER_PAGE = 7
RULES_ACTION_START = 1
RULES_ACTION_JSON = 2
RULES_ACTION_FINAL_MADE = 32
RULES_ACTION_FINAL_LOADED = 64
NOTIFICATION_CHECK_TIME = 5.0
NOTIFICATION_TIME_BEFORE_END = 90
NOTIFICATION_DISPLAY_TIME = 8
CHANNELBUG_CHECK_TIME = 15.0
MY_MONITOR = xbmc.Monitor()
MY_PLAYER  = xbmc.Player()


ACTION_PREVIOUS_MENU = (9, 10, 92, 216, 247, 257, 275, 61467, 61448,)


def setSetting(key,value):
    log('globals: setSetting, key = %s, value = %s'%(key,value))
    REAL_SETTINGS.setSetting(key,value)

def getSetting(key):
    # REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
    return REAL_SETTINGS.getSetting(key)
    
def getSettingBool(key):
    # REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
    try:
        return REAL_SETTINGS.getSettingBool(key)
    except:
        return REAL_SETTINGS.getSetting(key) == "true" 
    
def getSettingInt(key):
    # REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
    try: 
        return REAL_SETTINGS.getSettingInt(key)
    except:
        return int(REAL_SETTINGS.getSetting(key))

EXT_IMPORT       = getSettingBool('User_Import')
STORE_DURATION   = getSettingBool('Store_Duration')
STRICT_DURATION  = getSettingBool('Strict_Duration')
MAX_GUIDE_DAYS   = getSettingInt('Max_Days')
ENABLE_BCTS      = getSettingBool('Enable_Fillers')
PAGE_LIMIT       = getSettingInt('Page_Limit')
ACCURATE_DURATION= getSettingBool('Parse_Duration')
ENABLE_GROUPING  = getSettingBool('Enable_Grouping') 
MIN_ENTRIES      = int(PAGE_LIMIT//2)
UPDATE_OFFSET    = 3600#int((REAL_SETTINGS.getSettingInt('Update_Time') * 60) * 60) #seconds
INCLUDE_EXTRAS   = getSettingBool('Enable_Extras') 
INCLUDE_STRMS    = getSettingBool('Enable_Strms') 
CLIENT_MODE      = getSettingBool('Enable_Client') 
GROUP_TYPES      = ['TV Shows','TV Networks','TV Genres','Movie Genres','Mixed Genres','Movie Studios','Mixed','Other','Addons','UPNP','PVR','Action', 'Adult comedy', 'Adventure', 'Animation', 'Based on true life story', 'Biography', 'Comedy', 'Crime', 'Dark Comedy', 'Diaspora', 'Docu-drama', 'Documentary', 'Drama', 'Family', 'Fantasy', 'Heist', 'History', 'Horror', 'Kids', 'Melodrama', 'Murder Mystery', 'Musical', 'Mythology', 'Noir', 'Patriotism', 'Philosophy', 'Politics', 'Relationships', 'Religion', 'Revenge', 'Romance', 'Satire', 'Sci-fi', 'Short Films', 'Slapstick', 'Social', 'Spoof', 'Sports', 'Suspense', 'Terrorism', 'Thriller', 'Tragedy', 'War', 'Western']
if getSetting('User_Groups'): GROUP_TYPES.extend(getSetting('User_Groups').split('|'))
GROUP_TYPES.sort()
     
GLOBAL_RESOURCE_PACK_BUMPERS     = getSetting('Select_Resource_Networks')
GLOBAL_RESOURCE_PACK_COMMERICALS = getSetting('Select_Resource_Commericals')
GLOBAL_RESOURCE_PACK_TRAILERS    = getSetting('Select_Resource_Trailers')
GLOBAL_RESOURCE_PACK_RATINGS     = getSetting('Select_Resource_Ratings')
GLOBAL_RESOURCE_PACK             = {'rating'    :GLOBAL_RESOURCE_PACK_RATINGS,
                                    'bumper'    :GLOBAL_RESOURCE_PACK_BUMPERS,
                                    'commercial':GLOBAL_RESOURCE_PACK_COMMERICALS,
                                    'trailer'   :GLOBAL_RESOURCE_PACK_TRAILERS}
                     
                     
                     
@contextmanager
def busy_dialog():
    log('globals: busy_dialog')
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try: yield
    finally: xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

def notificationDialog(message, header=ADDON_NAME, sound=False, time=4000, icon=ICON):
    log('globals: notificationDialog: ' + message)
    try: xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
    except Exception as e:
        log("globals: notificationDialog Failed! " + str(e), xbmc.LOGERROR)
        xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        
def textviewer(msg, heading=ADDON_NAME, usemono=False):
    xbmcgui.Dialog().textviewer(heading, msg, usemono)
    
def yesnoDialog(message, heading=ADDON_NAME, nolabel='', yeslabel='', customlabel='', autoclose=0):
    return xbmcgui.Dialog().yesno(heading, message, nolabel, yeslabel, customlabel, autoclose)

def browseDialog(type=0, heading=ADDON_NAME, default='', shares='', mask='', options=None, useThumbs=True, treatAsFolder=False, prompt=True, multi=False):
    if prompt and not default:
        if options is None:
            options  = [{"label":"Video Playlists" , "label2":"Video Playlists"               , "default":"special://profile/playlists/video/" , "mask":'.xsp'     , "type":1, "multi":False},
                        {"label":"Music Playlists" , "label2":"Music Playlists"               , "default":"special://profile/playlists/music/" , "mask":'.xsp'     , "type":1, "multi":False},
                        {"label":"Video"           , "label2":"Video Sources"                 , "default":"library://video/"                   , "mask":VIDEO_EXTS, "type":0, "multi":False},
                        {"label":"Music"           , "label2":"Music Sources"                 , "default":"library://music/"                   , "mask":MUSIC_EXTS, "type":0, "multi":False},
                        {"label":"Pictures"        , "label2":"Picture Sources"               , "default":""                                   , "mask":IMAGE_EXTS, "type":0, "multi":False},
                        {"label":"Files"           , "label2":"File Sources"                  , "default":""                                   , "mask":""         , "type":0, "multi":False},
                        {"label":"Local"           , "label2":"Local Drives"                  , "default":""                                   , "mask":""         , "type":0, "multi":False},
                        {"label":"Network"         , "label2":"Local Drives and Network Share", "default":""                                   , "mask":""         , "type":0, "multi":False},
                        {"label":"Resources"       , "label2":"Resource Plugins"              , "default":""                                   , "mask":""         , "type":0, "multi":False}]
        listitems = [buildMenuListItem(option['label'],option['label2'],LOGO) for option in options]
        select    = selectDialog(listitems, 'Select Source Type', multi=False)
        if select >= 0:
            shares    = options[select]['label'].lower().replace("network","")
            mask      = options[select]['mask']
            type      = options[select]['type']
            multi     = options[select]['multi']
            default   = options[select]['default']
    log('globals: browseDialog, type = %s, heading= %s, shares= %s, mask= %s, useThumbs= %s, treatAsFolder= %s, default= %s'%(type, heading, shares, mask, useThumbs, treatAsFolder, default))
    if multi == True:
        # https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#ga856f475ecd92b1afa37357deabe4b9e4
        # type integer - the type of browse dialog.
        # 1	ShowAndGetFile
        # 2	ShowAndGetImage
        retval = xbmcgui.Dialog().browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)
    else:
        # https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#gafa1e339e5a98ae4ea4e3d3bb3e1d028c
        # type integer - the type of browse dialog.
        # 0	ShowAndGetDirectory
        # 1	ShowAndGetFile
        # 2	ShowAndGetImage
        # 3	ShowAndGetWriteableDirectory
        retval = xbmcgui.Dialog().browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)
    return retval
  
def inputDialog(message, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
    # Types:
    # - xbmcgui.INPUT_ALPHANUM (standard keyboard)
    # - xbmcgui.INPUT_NUMERIC (format: #)
    # - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
    # - xbmcgui.INPUT_TIME (format: HH:MM)
    # - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
    # - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
    retval = xbmcgui.Dialog().input(message, default, key, opt, close)
    return retval
    
def selectDialog(list, header=ADDON_NAME, preselect=None, useDetails=True, autoclose=0, multi=True):
    if multi == True:
        if preselect is None: preselect = []
        select = xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
    else:
        if preselect is None:  preselect = -1
        select = xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
    return select

def ProgressBGDialog(percent=0, control=None, message='', header=ADDON_NAME):
    if percent == 0 and control is None:
        control = xbmcgui.DialogProgressBG()
        control.create(header, message)
    elif control:
        if percent == 100 or control.isFinished(): return control.close()
        else: control.update(percent, header, message)
    return control
    
def log(msg, level=xbmc.LOGDEBUG):
    if not getSettingBool('Enable_Debugging') and level != xbmc.LOGERROR: return
    if   level == xbmc.LOGERROR: msg = '%s, %s'%((msg),traceback.format_exc())
    elif level == xbmc.LOGINFO:  setProperty("USER_LOG",'%s\n\n%s'%(msg,getProperty("USER_LOG")))
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,(msg)),level)
    
def hasPVR():
    return bool(xbmc.getCondVisibility('Pvr.HasTVChannels'))
    
def hasMusic():
    return bool(xbmc.getCondVisibility('Library.HasContent(Music)'))
    
def hasTV():
    return bool(xbmc.getCondVisibility('Library.HasContent(TVShows)'))
    
def hasMovie():
    return bool(xbmc.getCondVisibility('Library.HasContent(Movies)'))

def setBusy(state):
    setProperty("RUNNING",str(state))
    
def isBusy():
    return (getProperty("RUNNING") == "True")
    
def removeDUPS(lst):
    list_of_strings = [dumpJSON(d) for d in lst]
    list_of_strings = set(list_of_strings)
    return [loadJSON(s) for s in list_of_strings]
  
def dumpJSON(dict1, sortkey=True):
    if isinstance(dict1, basestring): return dict1
    return (json.dumps(dict1, sort_keys=sortkey))
    
def loadJSON(string1):
    if   isinstance(string1,dict): return string1
    try: return json.loads((string1.strip('\n').strip('\t').strip('\r')), strict=False)
    except Exception as e: log("globals: loadJSON failed! %s \n %s"%(e,string1), xbmc.LOGERROR)
    return {}
    
def sendJSON(command):
    log('globals: sendJSON, command = %s'%(command))
    response = loadJSON(xbmc.executeJSONRPC(command))
    log('globals: sendJSON, response = %s'%(response))
    return response

def buildMenuListItem(label1="", label2="", iconImage=None, url="", infoItem=None, artItem=None, propItem=None, oscreen=True, mType='video'):
    listitem  = xbmcgui.ListItem(label1, label2, path=url, offscreen=oscreen)
    iconImage = (iconImage or LOGO)
    if propItem: listitem.setProperties(propItem)
    if infoItem: listitem.setInfo(mType, infoItem)
    else: listitem.setInfo(mType,   {'mediatype': 'video',
                                     'Label' : label1,
                                     'Label2': label2,
                                     'Title' : label1})
    if artItem: listitem.setArt(artItem)
    else: listitem.setArt({'thumb': iconImage,
                           'icon' : iconImage})
    return listitem

def getPluginMeta(plugin):
    log('globals: plugin = %s'%(plugin))
    try:
        if '?' in plugin: plugin = plugin.split('?')[0]
        if plugin.startswith(('plugin://','resource://')):
            plugin = plugin.replace("plugin://","").replace("resource://","").strip('/')
        pluginID = xbmcaddon.Addon(plugin)
        return {'type':pluginID.getAddonInfo('type'),'name':pluginID.getAddonInfo('name'), 'version':pluginID.getAddonInfo('version'), 'path':pluginID.getAddonInfo('path'), 'author':pluginID.getAddonInfo('author'), 'icon':pluginID.getAddonInfo('icon'), 'fanart':pluginID.getAddonInfo('fanart'), 'id':pluginID.getAddonInfo('id'), 'description':(pluginID.getAddonInfo('description') or pluginID.getAddonInfo('summary'))}
    except Exception as e: log("globals, Failed! %s"%(e), xbmc.LOGERROR)
    return {}
        
def togglePVR(state='true'):
    return sendJSON('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":%s}, "id": 1}'%(PVR_CLIENT,state))

def brutePVR(override=False):
    if not override:
        if not yesnoDialog('%s ?'%(LANGUAGE(30065)%(getPluginMeta(PVR_CLIENT).get('name','')))): return
    togglePVR('false')
    xbmc.sleep(1000)
    togglePVR('true')
    return notificationDialog(LANGUAGE(30053))

def getPVR():
    try: return xbmcaddon.Addon(PVR_CLIENT)
    except: # backend disabled?
        togglePVR('true')
        xbmc.sleep(1000)
        return xbmcaddon.Addon(PVR_CLIENT)
        
def checkPVR():
    log('globals: checkPVR')
    #check for min. settings required
    addon = getPVR()
    check = [addon.getSetting('m3uRefreshMode')         == '1',
             # addon.getSetting('m3uRefreshHour')         == '%s'%(int((UPDATE_OFFSET/60)/60)),
             addon.getSetting('m3uRefreshIntervalMins') == '10',
             addon.getSetting('logoPathType')           == '0',
             addon.getSetting('logoPath')               == LOGO_LOC,
             addon.getSetting('m3uPathType')            == '0',
             addon.getSetting('m3uPath')                == M3UFLE,
             addon.getSetting('epgPathType')            == '0',
             addon.getSetting('epgPath')                == XMLTVFLE,
             addon.getSetting('genresPathType')         == '0',
             addon.getSetting('genresPath')             == GENREFLE]
    if False in check: configurePVR()
                 
def configurePVR(override=False):
    log('globals: configurePVR')
    if not override:
        if not yesnoDialog('%s ?'%(LANGUAGE(30012)%(getPluginMeta(PVR_CLIENT).get('name',''),ADDON_NAME,))): return
    try:
        addon = getPVR()
        addon.setSetting('m3uRefreshMode', '1')
        # addon.setSetting('m3uRefreshHour', '%s'%(int((UPDATE_OFFSET/60)/60)))
        addon.setSetting('m3uRefreshIntervalMins', '10')
        addon.setSetting('logoFromEpg', '1')
        addon.setSetting('logoPathType', '0')
        addon.setSetting('logoPath',  LOGO_LOC)
        addon.setSetting('m3uPathType', '0')
        addon.setSetting('m3uPath', M3UFLE)
        addon.setSetting('epgPathType', '0')
        addon.setSetting('epgPath', XMLTVFLE)
        addon.setSetting('epgTimeShift', '0')
        addon.setSetting('epgTSOverride', 'false')
        addon.setSetting('startNum', '1')
        addon.setSetting('useEpgGenreText', 'true')
        addon.setSetting('genresPathType', '0')
        addon.setSetting('genresPath', GENREFLE)
    except: return notificationDialog(LANGUAGE(30049)%(PVR_CLIENT))
    return notificationDialog(LANGUAGE(30053))
    
def hasSubtitle():
    return xbmc.getCondVisibility('VideoPlayer.HasSubtitles') == 1

def strpTime(datestring, format='%Y-%m-%d %H:%M:%S'):
    try: return datetime.datetime.strptime(datestring, format)
    except TypeError: return datetime.datetime.fromtimestamp(time.mktime(time.strptime(datestring, format)))

def getLocalTime():
    offset = (datetime.datetime.utcnow() - datetime.datetime.now())
    return time.time() + offset.total_seconds()

def getDeltaTime(time):
    datetime.datetime.fromtimestamp(time) + datetime.timedelta(time)

def escapeDirJSON(path):
    mydir = path
    if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
    return mydir

    
def buildItemListItem(item, mType='video', oscreen=True, playable=True):
    info       = item.copy()
    art        = info.get('art',{})
    streamInfo = item.get('streamdetails',{})
    properties = info.get('customproperties',{})
    uniqueid   = info.get('uniqueid',{})
    cast       = info.get('cast',[])
    
    info.pop('art'             ,{})
    info.pop('streamdetails'   ,{})
    info.pop('customproperties',{})
    info.pop('uniqueid'        ,{})
    info.pop('cast'            ,[])
              
    def cleanInfo(info):
        tmpInfo = info.copy()
        for key, value in tmpInfo.items():
            ptype = LISTITEM_TYPES.get(key,None)
            if ptype is None: 
                info.pop(key)
                properties[key] = value
                continue
            if not isinstance(value, ptype):
                info.update({key:ptype(value)})
        
    listitem = xbmcgui.ListItem(offscreen=oscreen)
    listitem.setLabel2(info.get('label2',''))
    listitem.setPath(item.get('file','')) # (item.get('file','') or item.get('url','') or item.get('path',''))
    listitem.setInfo(type=mType, infoLabels=cleanInfo(info))
    listitem.setArt(art)
    listitem.setCast(cast)
    listitem.setUniqueIDs(uniqueid)
    [listitem.setProperty(key, str(value)) for key, value in properties.items()]
    [listitem.addStreamInfo(key, value) for key, values in streamInfo.items() for value in values]
    if playable: listitem.setProperty("IsPlayable","true")
    return listitem
    
        
def isHD(item):
    if 'isHD' in item: return item['isHD']
    elif 'streamdetails' in item: 
        item = item.get('streamdetails',{})
        if 'video' in item and len(item.get('video')) > 0:
            videowidth  = int(item['video'][0]['width']  or '0')
            videoheight = int(item['video'][0]['height'] or '0')
            if videowidth >= 1280 and videoheight >= 720: return True  
    return False

    
def is3D(item):
    if 'is3D' in item: return item['is3D']
    if 'streamdetails' in item: item = item.get('streamdetails',{})
    if 'video' in item and item.get('video') != [] and len(item.get('video')) > 0:
        stereomode = (item['video'][0]['stereomode'] or '')
        if len(stereomode) > 0: return True
    return False
         
def getThumb(file):
    return (file['art'].get('tvshow.landscape','') or 
            file['art'].get('tvshow.fanart','')    or 
            file['art'].get('tvshow.poster','')    or
            file['art'].get('tvshow.thumb','')     or 
            file['art'].get('landscape','')        or
            file['art'].get('fanart','')           or 
            file['art'].get('poster','')           or
            file['art'].get('thumb','')            or
            FANART)

def getProperty(key, id=10000):
    try: 
        key = '%s.%s'%(ADDON_ID,key)
        value = xbmcgui.Window(id).getProperty(key)
        if not key.endswith("USER_LOG"):
            if value: log("globals: getProperty, key = " + key + ", value = " + value)
        return value
    except Exception as e: return ''
          
def setProperty(key, value, id=10000):
    key = '%s.%s'%(ADDON_ID,key)
    if not key.endswith("USER_LOG"):
        log("globals: setProperty, key = " + key + ", value = " + value)
    try: xbmcgui.Window(id).setProperty(key, value)
    except Exception as e: log("globals: setProperty, Failed! " + str(e), xbmc.LOGERROR)

def clearProperty(key, id=10000):
    key = '%s.%s'%(ADDON_ID,key)
    xbmcgui.Window(id).clearProperty(key)

def assertLST(lst1,lst2): #test if both lists match. 
    assertBool = len(diffLST(lst1,lst2)) == 0
    log('globals: assertLST = %s'%(assertBool))
    return assertBool
    
def diffLST(lst1, lst2): 
    difference = (list(set(lst1) - set(lst2)))
    log('globals: diffLST = %s'%(difference))
    return difference
    
def assertDICT(dict1,dict2,return_diff=False): #test if both dicts match.
    difference = diffDICT(dict1,dict2)
    assertBool = len(difference) == 0
    log('globals: assertDICT = %s'%(assertBool))
    if return_diff: return assertBool, difference
    return assertBool
    
def diffDICT(dict1, dict2): 
    intersec = [item for item in dict1 if item in dict2]
    difference = [item for item in chain(dict1,dict2) if item not in intersec]
    log('globals: diffDICT = %s'%(dumpJSON(difference)))
    return difference
    
def mergeDICT(dict1, dict2):
    return [{**u, **v} for u, v in zip_longest(dict1, dict2, fillvalue={})]
    
def isPseudoTV():
    #todo improve check
    isPseudoTV = len(getProperty('channel_item')) > 0
    log('globals: isPseudoTV = %s'%(isPseudoTV))
    return isPseudoTV
  
def setCurrentChannelItem(item):
    setProperty('channel_item',dumpJSON(item))
    
def getCurrentChannelItem():  
    xbmc.sleep(500)
    return loadJSON(getProperty('channel_item'))
  
def clearCurrentChannelItem():
    clearProperty('channel_item')
  
def getChannelID(name, path):
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s'%(name, hashlib.md5(path.encode('utf-8')))
    return '%s@%s'%((binascii.hexlify(tmpid.encode("utf-8"))[:32]).decode("utf-8"),slugify(ADDON_NAME))

def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text

def interleave(*args): #interleave multi-lists, while preserving order
    try:
        iters = list(map(iter, args))
        while iters and not MY_MONITOR.abortRequested():
            it = random.choice(iters)
            try:
                yield next(it)
            except StopIteration:
                iters.remove(it)
    except Exception as e: 
        log("interleave, Failed! %s"%(e), xbmc.LOGERROR)
        yield list(chain.from_iterable(izip_longest(*args)))[0]
     
def sysListItem():
    return sys.listitem
     
def isSubtitle():
    return bool(xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled'))
    
def installAddon(id):
    if xbmc.getCondVisibility('System.HasAddon("%s")'%(id)) == 1: return
    xbmc.executebuiltin('InstallAddon("%s")'%(id))
        
def getRandomPage(limit,total=50):
    page = random.randrange(0, total, limit)
    log('global: getRandomPage, page = %s'%(page))
    return page, page+limit

def isPlaylistRandom():
    return xbmc.getInfoLabel('Playlist.Random').lower() == 'random' # Disable auto playlist shuffling if it's on
    
def isPlaylistRepeat():
    return xbmc.getInfoLabel('Playlist.IsRepeat').lower() == 'true' # Disable auto playlist repeat if it's on #todo

def findItemsIn(items, values, item_key='getLabel', val_key='', index=True):
    log("globals: findItemsIn, values = %s, key = %s, val_key = %s, index = %s"%(values, item_key, val_key, index))
    matches = []
    def match(fidx,fitem,fkey,fvalue):
        if fkey.lower() == fvalue.lower():
            matches.append(fidx if index else fitem)
        
    if not values: return [-1]
    for idx, item in enumerate(items):
        for value in values:
            if isinstance(value,dict): value = value.get(val_key,'')
            if isinstance(item,xbmcgui.ListItem):
                if   item_key == 'getLabel':  
                    match(idx,item,item.getLabel() ,value)
                elif item_key == 'getLabel2': 
                    match(idx,item,item.getLabel2(),value)
            elif isinstance(item,dict):       
                match(idx,item,item.get(item_key,''),value)
            else:                             
                match(idx,item,item,value)
    log("globals: findItemsIn, matches = %s"%(matches))
    return matches

def roundToHalfHour(stime,offset=30): # round the given time down to the nearest
    n = datetime.datetime.fromtimestamp(stime)
    delta = datetime.timedelta(minutes=offset)
    if n.minute > (offset-1): n = n.replace(minute=offset, second=0, microsecond=0)
    else: n = n.replace(minute=0, second=0, microsecond=0)
    return time.mktime(n.timetuple())

def roundToHour(stime,offset=30): # round the given time up to the nearest
    n = datetime.datetime.fromtimestamp(stime)
    n = (n.replace(second=0, microsecond=0, minute=0, hour=n.hour) + datetime.timedelta(hours=n.minute//30))
    return time.mktime(n.timetuple())

def pagination(list, end):
    for start in xrange(0, len(list), end):
        yield seq[start:start+end]
        
class PoolHelper:
    def __init__(self):
        if ENABLE_POOL: 
            self.pool = ThreadPool(CORES)
            log("PoolHelper: CPU CORES = " + str(CORES))
        else: 
            log("PoolHelper: ThreadPool Disabled")
        

    def runSelf(self, func):
        return func()
        
        
    def poolList(self, method, items=None, args=None, chunk=25):
        log("PoolHelper: poolList")
        results = []
        if ENABLE_POOL:
            if items is None and args is None: 
                results = self.pool.map(self.runSelf, method)#, chunksize=chunk)
            elif args is not None: 
                results = self.pool.map(method, zip(items,repeat(args)))
            elif items: 
                results = self.pool.map(method, items)#, chunksize=chunk)
            self.pool.close()   
            self.pool.join()
        else:
            if items is None and args is None: 
                results = [self.runSelf(func) for func in method]
            elif args is not None: 
                results = [method((item, args)) for item in items]
            elif items: 
                results = [method(item) for item in items]
        return filter(None, results)