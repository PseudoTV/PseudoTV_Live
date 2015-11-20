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


import os, re, sys, time, zipfile, threading, requests, random, traceback, pyfscache
import urllib, urllib2,cookielib, base64, fileinput, shutil, socket, httplib, json, urlparse, HTMLParser
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon
import time, _strptime, string, datetime, ftplib, hashlib, smtplib, feedparser, imp

from functools import wraps
from Globals import * 
from FileAccess import FileAccess
from Queue import Queue
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders
from xml.dom.minidom import parse, parseString
from urllib import unquote, quote
from urllib2 import HTTPError, URLError

socket.setdefaulttimeout(30)

try:
    import gc
except:
    pass

# Commoncache plugin import
try:
    import StorageServer
except Exception,e:
    import storageserverdummy as StorageServer

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

# Videowindow filepaths
Path = xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', '1080i'))
flePath = xbmc.translatePath(os.path.join(Path, 'custom_script.pseudotv.live_9506.xml'))
PTVL_SKIN_WINDOW_FLE = ['script.pseudotv.live.EPG.xml','script.pseudotv.live.Ondemand.xml','script.pseudotv.live.DVR.xml','script.pseudotv.live.Apps.xml']     
VWPath = xbmc.translatePath(os.path.join(XBMC_SKIN_LOC, 'custom_script.pseudotv.live_9506.xml'))  
DSPath = xbmc.translatePath(os.path.join(XBMC_SKIN_LOC, 'DialogSeekBar.xml'))

# Videowindow Patch
a = '<!-- PATCH START -->'
b = '<!-- PATCH START --><!--'
c = '<!-- PATCH END -->'
d = '--><!-- PATCH END -->'

# Seekbar Patch
v = ' '
w = '<visible>Window.IsActive(fullscreenvideo) + !Window.IsActive(script.pseudotv.TVOverlay.xml) + !Window.IsActive(script.pseudotv.live.TVOverlay.xml)</visible>'
y = '</defaultcontrol>'
z = '</defaultcontrol>\n    <visible>Window.IsActive(fullscreenvideo) + !Window.IsActive(script.pseudotv.TVOverlay.xml) + !Window.IsActive(script.pseudotv.live.TVOverlay.xml)</visible>'

################
# Github Tools #
################
     
def isKodiRepo(plugin=''):
    log("utils: isKodiRepo")
    # parse kodi repo, collect video, music plugins
    # if necessary limit plugins to kodi approved.
    if plugin[0:9] == 'plugin://':
        plugin = plugin.replace("plugin://","")
        addon = splitall(plugin)[0]
    else:
        addon = plugin  
        
    # kodi repo urls
    dharma = 'https://github.com/xbmc/repo-plugins/tree/dharma'
    eden = 'https://github.com/xbmc/repo-plugins/tree/eden'
    frodo = 'https://github.com/xbmc/repo-plugins/tree/frodo'
    gotham = 'https://github.com/xbmc/repo-plugins/tree/gotham'
    helix = 'https://github.com/xbmc/repo-plugins/tree/helix'
    isengard = 'https://github.com/xbmc/repo-plugins/tree/isengard'
    jarvis = 'https://github.com/xbmc/repo-plugins/tree/jarvis'
    
    repoItems = []
    repoItems = fillGithubItems(dharma)
    repoItems += fillGithubItems(eden)
    repoItems += fillGithubItems(frodo)
    repoItems += fillGithubItems(gotham)
    repoItems += fillGithubItems(helix)
    repoItems += fillGithubItems(isengard)
    repoItems += fillGithubItems(jarvis)
    
    RepoPlugins = []
    for i in range(len(repoItems)):
        if (repoItems[i]).lower().startswith('plugin.video.'):
            RepoPlugins.append((repoItems[i]).split(' ')[0])
        elif (repoItems[i]).lower().startswith('plugin.music.'):
            RepoPlugins.append((repoItems[i]).split(' ')[0])
    if addon in RepoPlugins:
        return True
    else:
        return False

def fillGithubItems(url, ext=None, removeEXT=False):
    log("utils: fillGithubItems, url = " + url)
    Sortlist = []
    show_busy_dialog()
    try:
        list = []
        catlink = re.compile('title="(.+?)">').findall(read_url_cached(url))
        for i in range(len(catlink)):
            link = catlink[i]
            name = (catlink[i]).lower()
            if ext != None:
                if ([x.lower for x in ext if name.endswith(x)]):
                    if removeEXT == True:
                        link = os.path.splitext(os.path.basename(link))[0]
                    list.append(link.replace('&amp;','&'))
            else:
                list.append(link.replace('&amp;','&'))
        Sortlist = sorted_nicely(list) 
        log("utils: fillGithubItems, found %s items" % str(len(Sortlist)))
    except Exception,e:
        log("utils: fillGithubItems, Failed! " + str(e))
        log(traceback.format_exc(), xbmc.LOGERROR)
    hide_busy_dialog()
    return Sortlist

#############
# Art Tools #
#############

# def ArtServiceQueue(self):
    # ADDON_SETTINGS.loadSettings()
    # ArtLST = []
    # for i in range(1000):
        # lineLST = []
        # try:
            # chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(i+1) + '_type'))
            # chname = (self.channels[i+1 - 1].name)
            # fle = xbmc.translatePath(os.path.join(LOCK_LOC, ("channel_" + str(i+1) + '.m3u')))  
            # if chtype != 9999:
                # if FileAccess.exists(fle):
                    # f = FileAccess.open(fle, 'r')
                    # lineLST = f.readlines()
                    # lineLST.pop(0) #Remove unwanted first line '#EXTM3U'
                    # for n in range(len(lineLST)):
                        # line = lineLST[n]
                        # if line[0:7] == '#EXTINF':
                            # liveid = line.rsplit('//',1)[1]
                            # type = liveid.split('|')[0]
                            # id = liveid.split('|')[1]
                            # dbid, epid = splitDBID(liveid.split('|')[2])
                        # elif line[0:7] not in ['#EXTM3U', '#EXTINF']:
                            # mpath = getMpath(line)
                        # if type and mpath:
                            # ArtLST.append([type, chtype, chname, id, dbid, mpath])
        # except Exception,e:
            # log("utils: ArtServiceQueue, Failed! " + str(e))
            # pass
            
    # # shuffle list to evenly distribute queue
    # random.shuffle(ArtLST)
    # log('utils: ArtServiceQueue, ArtLST Count = ' + str(len(ArtLST)))
    # return ArtLST

        
    # def ArtService(self):
        # if getProperty("PseudoTVRunning") != "True" and getProperty("ArtService_Running") == "false":
            # setProperty("PseudoTVRunning","True")
            # setProperty("ArtService_Running","true")
            # start = datetime.datetime.today()
            # ArtLst = self.ArtServiceQueue() 
            # Types = []
            # cnt = 0
            # subcnt = 0
            # totcnt = 0
            # lstcnt = len(ArtLst)
            # stdNotify("Artwork Spooler Started")

            # # Clear Artwork Cache Folders
            # if REAL_SETTINGS.getSetting("ClearLiveArtCache") == "true":
                # artwork.delete("%") 
                # artwork1.delete("%")
                # artwork2.delete("%")
                # artwork3.delete("%")
                # artwork4.delete("%")
                # artwork5.delete("%")
                # artwork6.delete("%")
                # log('utils: ArtService, ArtCache Purged!')
                # REAL_SETTINGS.setSetting('ClearLiveArtCache', "false")  
                # stdNotify("Artwork Cache Cleared")

            # artEXT_Types = ['type1','type2','type3','type4']
            # for a in range(len(artExT_Types)):
                # try:
                    # Types.append(getProperty(("OVERLAY.%s")%artEXT_Types[a]))
                # except:
                    # pass
                # try:
                    # Types.append(getProperty(("EPG.%s")%artEXT_Types[a]))
                # except:
                    # pass
            
            # Types = remove_duplicates(Types)
            # log('utils: ArtService, Types = ' + str(Types))  
            
            # for i in range(lstcnt): 
                # setDefault = ''
                # setImage = ''
                # setBug = ''
                # lineLST = ArtLst[i]
                # type = lineLST[0]
                # chtype = lineLST[1]
                # chname = lineLST[2]
                # id = lineLST[3]
                # dbid = lineLST[4]
                # mpath = lineLST[5]
                # cnt += 1
                
                # self.Artdownloader.FindLogo(chtype, chname, mpath)
                # for n in range(len(Types)):
                    # self.Artdownloader.FindArtwork(type, chtype, chname, id, dbid, mpath, EXTtype(Types[n]))

                # if lstcnt > 5000:
                    # quartercnt = int(round(lstcnt / 4))
                # else:
                    # quartercnt = int(round(lstcnt / 2))
                # if cnt > quartercnt:
                    # totcnt = cnt + totcnt
                    # subcnt = lstcnt - totcnt
                    # percnt = int(round((float(subcnt) / float(lstcnt)) * 100))
                    # cnt = 0
                    # stdNotify(("Artwork Spooler"+' % '+"%d complete" %percnt) )

            # stop = datetime.datetime.today()
            # finished = stop - start
            # setProperty("ArtService_Running","false")
            # setProperty("PseudoTVRunning","False")
            # REAL_SETTINGS.setSetting("ArtService_LastRun",str(stop))
            # stdNotify(("Artwork Spooled in %d seconds" %finished.seconds))
            # log('utils: ArtService, ' + ("Artwork Spooled in %d seconds" %finished.seconds))

##############
# LOGO Tools #
##############

def CleanCHname(text):
    text = text.replace("AE", "A&E")
    text = text.replace(" (uk)", "")
    text = text.replace(" (UK)", "")
    text = text.replace(" (us)", "")
    text = text.replace(" (US)", "")
    text = text.replace(" (ca)", "")
    text = text.replace(" (CA)", "")
    text = text.replace(" (en)", "")
    text = text.replace(" (EN)", "")
    text = text.replace(" hd", "")
    text = text.replace(" HD", "")
    text = text.replace(" PVR", "")
    text = text.replace(" LiveTV", "") 
    text = text.replace(" USTV", "")
    text = text.replace(" USTVnow", "")  
    text = text.replace(" USTVNOW", "") 
    # # try removing number from channel ie NBC2 = NBC
    # try:
        # text = (re.compile('(.+?)(\d{1})$').findall(text))[0][0]
    # except:
        # pass
    return text

def FindLogo_Thread(data):
    log("utils: FindLogo_Thread, " + str(data))
    chtype = int(data[0])
    chname = data[1]
    url = ''
    LogoName = chname + '.png'
    LogoFolder = os.path.join(LOGO_LOC,LogoName)
    log("utils: FindLogo_Thread, LogoFolder = " + LogoFolder)
    
    if FileAccess.exists(LOGO_LOC) == False:
        FileAccess.makedirs(LOGO_LOC)
        
    if chtype in [0,1,8,9]:
        log("utils: FindLogo_Thread, findLogodb")
        user_region = REAL_SETTINGS.getSetting('limit_preferred_region')
        user_type = REAL_SETTINGS.getSetting('LogoDB_Type')
        useMix = REAL_SETTINGS.getSetting('LogoDB_Fallback') == "true"
        useAny = REAL_SETTINGS.getSetting('LogoDB_Anymatch') == "true"
        url = findLogodb(chname, user_region, user_type, useMix, useAny)
        if url:
            GrabLogo(url, chname)
    if chtype in [0,1,2,3,4,5,8,9,12,13,14]:
        log("utils: FindLogo_Thread, findGithubLogo")
        url = findGithubLogo(chname)
        if url:
            GrabLogo(url, chname)
    mpath = getMpath(data[2])
    if mpath and (chtype == 6):
        log("utils: FindLogo_Thread, local logo")
        smpath = mpath.rsplit('/',2)[0] #Path Above mpath ie Series folder
        artSeries = xbmc.translatePath(os.path.join(smpath, 'logo.png'))
        artSeason = xbmc.translatePath(os.path.join(mpath, 'logo.png'))
        if FileAccess.exists(artSeries): 
            url = artSeries
        elif FileAccess.exists(artSeason): 
            url = artSeason
        if url:
            GrabLogo(url, chname) 
  
def FindLogo(chtype, chname, mediapath=None):
    log("utils: FindLogo")
    try:
        if REAL_SETTINGS.getSetting('Enable_FindLogo') == "true" and isLowPower() != True:
            data = [chtype, chname, mediapath]
            FindLogoThread = threading.Timer(0.5, FindLogo_Thread, [data])
            FindLogoThread.name = "FindLogoThread"
            if FindLogoThread.isAlive():
                FindLogoThread.cancel()
                FindLogoThread.join()            
            FindLogoThread.start()
    except Exception,e:
        log('utils: FindLogo, Failed!,' + str(e))
        pass   
         
def FindLogo_Default(chname, chpath):
    log('utils: FindLogo_Default')
         
def findGithubLogo(chname): 
    log("utils: findGithubLogo")
    url = ''
    baseurl='https://github.com/PseudoTV/PseudoTV_Logos/tree/master/%s' % (chname[0]).upper()
    Studiolst = fillGithubItems(baseurl, '.png', removeEXT=True)
    if not Studiolst:
        miscurl='https://github.com/PseudoTV/PseudoTV_Logos/tree/master/0'
        Misclst = fillGithubItems(miscurl, '.png', removeEXT=True)
        for i in range(len(Misclst)):
            Studio = Misclst[i]
            cchname = CleanCHname(chname)
            if uni((Studio).lower()) == uni(cchname.lower()):
                url = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/0/'+((Studio+'.png').replace('&','&amp;').replace(' ','%20'))
                log('utils: findGithubLogo, Logo Match: ' + Studio.lower() + ' = ' + (Misclst[i]).lower())
                break
    else:
        for i in range(len(Studiolst)):
            Studio = Studiolst[i]
            cchname = CleanCHname(chname)
            if uni((Studio).lower()) == uni(cchname.lower()):
                url = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/'+chname[0]+'/'+((Studio+'.png').replace('&','&amp;').replace(' ','%20'))
                log('utils: findGithubLogo, Logo Match: ' + Studio.lower() + ' = ' + (Studiolst[i]).lower())
                break
    return url
           
def findLogodb(chname, user_region, user_type, useMix=True, useAny=True):
    try:
        clean_chname = (CleanCHname(chname))
        urlbase = 'http://www.thelogodb.com/api/json/v1/%s/tvchannel.php?s=' % LOGODB_API_KEY
        chanurl = (urlbase+clean_chname).replace(' ','%20')
        log("utils: findLogodb, chname = " + chname + ', clean_chname = ' + clean_chname + ', url = ' + chanurl)
        typelst =['strLogoSquare','strLogoSquareBW','strLogoWide','strLogoWideBW','strFanart1']
        user_type = typelst[int(user_type)]
        detail = re.compile("{(.*?)}", re.DOTALL ).findall(read_url_cached(chanurl))
        MatchLst = []
        mixRegionMatch = []
        mixTypeMatch = []
        image = ''
        for f in detail:
            try:
                regions = re.search('"strCountry" *: *"(.*?)"', f)
                channels = re.search('"strChannel" *: *"(.*?)"', f)
                if regions:
                    region = regions.group(1)
                if channels:
                    channel = channels.group(1)
                    for i in range(len(typelst)):
                        types = re.search('"'+typelst[i]+'" *: *"(.*?)"', f)
                        if types:
                            type = types.group(1)
                            if channel.lower() == clean_chname.lower():
                                if typelst[i] == user_type:
                                    if region.lower() == user_region.lower():
                                        MatchLst.append(type.replace('\/','/'))
                                    else:
                                        mixRegionMatch.append(type.replace('\/','/'))
                                else:
                                    mixTypeMatch.append(type.replace('\/','/'))
            except Exception,e:
                pass
                
        if len(MatchLst) == 0:
            if useMix == True and len(mixRegionMatch) > 0:
                random.shuffle(mixRegionMatch)
                image = mixRegionMatch[0]
                log('utils: findLogodb, Logo NOMATCH useMix: ' + str(image))
            if not image and useAny == True and len(mixTypeMatch) > 0:
                random.shuffle(mixTypeMatch)
                image = mixTypeMatch[0]
                log('utils: findLogodb, Logo NOMATCH useAny: ' + str(image))
        else:
            random.shuffle(MatchLst)
            image = MatchLst[0]
            log('utils: findLogodb, Logo Match: ' + str(image))
        return image 
    except Exception,e:
        log("utils: findLogodb, Failed! " + str(e))

def hasAPI(key):
    if isPlugin(key) == True:
        params = decodeString('Im1ldGhvZCI6IkFkZG9ucy5TZXRBZGRvbkVuYWJsZWQiLCJwYXJhbXMiOnsiYWRkb25pZCI6IiVzIiwiZW5hYmxlZCI6ZmFsc2V9')
        set_Kodi_JSON(params %key)
        
def GrabLogo(url, Chname):
    log("utils: GrabLogo, url = " + url)        
    try:
        LogoFile = os.path.join(LOGO_LOC, Chname + '.png')
        url = url.replace('.png/','.png').replace('.jpg/','.jpg')
        log("utils: GrabLogo, LogoFile = " + LogoFile)
       
        if REAL_SETTINGS.getSetting('LogoDB_Override') == "true":
            try:
                FileAccess.delete(LogoFile)
                log("utils: GrabLogo, removed old logo")   
            except:
                pass
        
        if FileAccess.exists(LogoFile) == False:
            log("utils: GrabLogo, downloading new logo")   
            if url.startswith('image'):
                url = (unquote(url)).replace("image://",'')
                if url.startswith('http'):
                    return download_silent(url, LogoFile)
                else:
                    FileAccess.copy(url, LogoFile) 
            elif url.startswith('http'):
                return download_silent(url, LogoFile)
            else:
                return FileAccess.copy(xbmc.translatePath(url), LogoFile) 
    except Exception,e:
        log("utils: GrabLogo, Failed! " + str(e))
     
#######################
# Communication Tools #
#######################

def GA_Request():
    log("GA_Request")
    # if REAL_SETTINGS.getSetting('ga_disable') == 'false':
    """
    Simple proof of concept code to push data to Google Analytics.
    Related blog posts:
     * https://medium.com/python-programming-language/80eb9691d61f
    """
    try:
        PROPERTY_ID = os.environ.get("GA_PROPERTY_ID", "UA-67386980-3")

        if not REAL_SETTINGS.getSetting('Visitor_GA'):
            REAL_SETTINGS.setSetting('Visitor_GA', str(random.randint(0, 0x7fffffff)))
        VISITOR = REAL_SETTINGS.getSetting("Visitor_GA")
        
        OPTIONS = ['PTVL:'+str(ADDON_VERSION)+'']
        OPTIONS = OPTIONS + ['USER:'+str(VISITOR)+'']
        OPTIONS = OPTIONS + ['KODI:'+str(getXBMCVersion())+'']
        OPTIONS = OPTIONS + ['OS:'+getProperty("PTVL.Platform")+'']
        
        if getProperty("Verified_Donor") == "true":
            OPTIONS = OPTIONS + ['DONOR:'+(REAL_SETTINGS.getSetting('Donor_UP')).split(':')[0]]
        
        if getProperty("Verified_Community") == "true":
            OPTIONS = OPTIONS + ['COM:'+REAL_SETTINGS.getSetting('Gmail_User')]
                    
        if isContextInstalled():
            OPTIONS = OPTIONS + ['CM:True']
            
        if isLowPower():
            OPTIONS = OPTIONS + ['LP:True']

        OPTIONLST = "/".join(OPTIONS)
        DATA = {"utmwv": "5.2.2d",
        "utmn": str(random.randint(1, 9999999999)),
        "utmp": OPTIONLST,
        "utmac": PROPERTY_ID,
        "utmcc": "__utma=%s;" % ".".join(["1", VISITOR, "1", "1", "1", "1"])}
 
        URL = urlparse.urlunparse(("http",
        "www.google-analytics.com",
        "/__utm.gif",
        "",
        urllib.urlencode(DATA),
        ""))
        urllib2.urlopen(URL).info()
    except Exception,e:  
        log("GA_Request Failed" + str(e), xbmc.LOGERROR)

def UpdateRSS():
    log('utils: UpdateRSS')
    try:
        UpdateRSSthread = threading.Timer(0.5, UpdateRSS_Thread)
        UpdateRSSthread.name = "UpdateRSSthread"
        if UpdateRSSthread.isAlive():
            UpdateRSSthread.cancel()      
        UpdateRSSthread.start()
    except Exception,e:
        log('utils: UpdateRSS, Failed!,' + str(e))
        pass   
          
def UpdateRSS_Thread():
    log('utils: UpdateRSS_Thread')
    now  = datetime.datetime.today()
    try:
        UpdateRSS_LastRun = getProperty("UpdateRSS_NextRun")
        if not UpdateRSS_LastRun:
            raise Exception()
    except Exception,e:
        UpdateRSS_LastRun = "1970-01-01 23:59:00.000000"
        setProperty("UpdateRSS_NextRun",UpdateRSS_LastRun)

    try:
        SyncUpdateRSS = datetime.datetime.strptime(UpdateRSS_LastRun, "%Y-%m-%d %H:%M:%S.%f")
    except:
        SyncUpdateRSS = datetime.datetime.strptime("1970-01-01 23:59:00.000000", "%Y-%m-%d %H:%M:%S.%f")
    
    if now > SyncUpdateRSS:
        ##Push MSG
        try:
            pushlist = ''
            pushrss = 'http://raw.githubusercontent.com/Lunatixz/XBMC_Addons/master/push_msg.xml'
            file = open_url(pushrss)
            pushlist = file.read().replace('\n','').replace('\r','').replace('\t','')
            file.close()
        except Exception,e:
            log('utils: UpdateRSS_Thread, pushlist Failed! ' + str(e))
        ##Github RSS
        try:
            gitlist = ''
            gitrss = 'http://github.com/Lunatixz.atom'
            d = feedparser.parse(gitrss)
            header = (d['feed']['title']).replace(' ',' Github ')
            post = d['entries'][0]['title']
            for post in d.entries:
                try:
                    if post.title.startswith('Lunatixz pushed to master at Lunatixz/XBMC_Addons'):
                        date = time.strftime("%m.%d.%Y @ %I:%M %p", post.date_parsed)
                        title = (post.title).replace('Lunatixz pushed to master at ','').replace('Lunatixz/XBMC_Addons','Updated repository plugins on')
                        gitlist = (header + ' - ' + title + ": " + date + "   ").replace('&amp;','&')
                        break
                except:
                    pass
        except Exception,e:
            log('utils: UpdateRSS_Thread, gitlist Failed! ' + str(e))
        gitlist += 'Follow @PseudoTV_Live on Twitter'
        ##Twitter RSS
        try:
            twitlist = []
            #twitrss ='http://feedtwit.com/f/pseudotv_live'
            twitrss = 'http://twitrss.me/twitter_user_to_rss/?user=pseudotv_live'
            e = feedparser.parse(twitrss)
            header = ((e['feed']['title']) + ' - ')
            twitlist = header.replace('Twitter Search / pseudotv_live','@PseudoTV_Live Twitter Activity')
            for tost in e.entries:
                try:
                    if '#PTVLnews' in tost.title:
                        date = time.strftime("%m.%d.%Y @ %I:%M %p", tost.published_parsed)
                        twitlist += (date + ": " + tost.title + "   ").replace('&amp;','&')
                except:
                    pass
        except Exception,e:
            log('utils: UpdateRSS_Thread, twitlist Failed! ' + str(e))
        UpdateRSS_NextRun = ((now + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f"))
        log('utils: UpdateRSS, Now = ' + str(now) + ', UpdateRSS_NextRun = ' + str(UpdateRSS_NextRun))
        setProperty("UpdateRSS_NextRun",str(UpdateRSS_NextRun))
        setProperty("twitter.1.label", pushlist)
        setProperty("twitter.2.label", gitlist)
        setProperty("twitter.3.label", twitlist) 

# Adapted from KodeKarnage's lazytv
def sendShout():
    thyme = time.time()
    recipient = 'pseudotvsubmit@gmail.com'
    
    body = '<table border="1">'
    body += '<tr><td>%s</td></tr>' % "I'm using the addon!"
    body += '</table>'
    
    msg = MIMEText(body, 'html')
    msg['Subject'] = 'LazyTV +1  %s' % thyme
    msg['From'] = 'LazyTV'
    msg['To'] = recipient
    msg['X-Mailer'] = 'LazyTV Shout Out %s' % thyme

    smtp = smtplib.SMTP('alt4.gmail-smtp-in.l.google.com')
    smtp.sendmail(msg['From'], msg['To'], msg.as_string(9))
    smtp.quit()

def sendGmail(subject, body, attach):
    GAuser = REAL_SETTINGS.getSetting('Visitor_GA')
    recipient = 'pseudotvsubmit@gmail.com'
    sender = REAL_SETTINGS.getSetting('Gmail_User')
    password = REAL_SETTINGS.getSetting('Gmail_Pass')
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    
    if attach:
        log("utils: sendGmail w/Attachment")
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject + ", From:" + GAuser
        msg.attach(MIMEText(body))
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(open(attach, 'rb').read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition',
               'attachment; filename="%s"' % os.path.basename(attach))
        msg.attach(part)
        mailServer = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        mailServer.ehlo()
        mailServer.starttls()
        mailServer.ehlo()
        mailServer.login(sender, password)
        mailServer.sendmail(sender, recipient, msg.as_string())
        # Should be mailServer.quit(), but that crashes...
        mailServer.close()
    else:
        log("utils: sendGmail")
        body = "" + body + ""
        subject = subject + ", From:" + GAuser
        headers = ["From: " + sender,
                   "Subject: " + subject,
                   "To: " + recipient,
                   "MIME-Version: 1.0",
                   "Content-Type: text/html"]
        headers = "\r\n".join(headers)
        session = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)        
        session.ehlo()
        session.starttls()
        session.ehlo
        session.login(sender, password)
        session.sendmail(sender, recipient, headers + "\r\n\r\n" + body)
        session.quit()
     
##################
#   URL Tools    #
##################

def _pbhook(numblocks, blocksize, filesize, dp, start_time):
    try: 
        percent = min(numblocks * blocksize * 100 / filesize, 100) 
        currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
        kbps_speed = numblocks * blocksize / (time.time() - start_time) 
        if kbps_speed > 0: 
            eta = (filesize - numblocks * blocksize) / kbps_speed 
        else: 
            eta = 0 
        kbps_speed = kbps_speed / 1024 
        total = float(filesize) / (1024 * 1024) 
        mbs = '%.02f MB of %.02f MB' % (currently_downloaded, total) 
        e = 'Speed: %.02f Kb/s ' % kbps_speed 
        e += 'ETA: %02d:%02d' % divmod(eta, 60) 
        dp.update(percent, mbs, e)
    except: 
        percent = 100 
        dp.update(percent) 
    if dp.iscanceled(): 
        dp.close() 
  
def download(url, dest, dp = None):
    log('download')
    if not dp:
        dp = xbmcgui.DialogProgress()
        dp.create("PseudoTV Live","Downloading & Installing Files", ' ', ' ')
    dp.update(0)
    start_time=time.time()
    try:
        urllib.urlretrieve(url, dest, lambda nb, bs, fs: _pbhook(nb, bs, fs, dp, start_time))
    except Exception,e:
        log('utils: download, Failed!,' + str(e))
     
def download_silent_thread(data):
    log('download_silent_thread')
    try:
        urllib.urlretrieve(data[0], data[1])
    except Exception,e:
        log('utils: download_silent_thread, Failed!,' + str(e))
         
def download_silent(url, dest):
    log('download_silent')
    try:
        data = [url, dest]
        download_silentThread = threading.Timer(0.5, download_silent_thread, [data])
        download_silentThread.name = "download_silentThread"
        if download_silentThread.isAlive():
            download_silentThread.cancel()
            download_silentThread.join()
        download_silentThread.start()
    except Exception,e:
        log('utils: download_silent, Failed!,' + str(e))
        
@cache_daily
def read_url_cached(url, userpass=False, return_type='read'):
    log("utils: read_url_cached")
    try:
        if return_type == 'readlines':
            response = open_url(url, userpass).readlines()
        else:
            response = open_url(url, userpass).read()
        return response
    except Exception,e:
        log('utils: read_url_cached, Failed!,' + str(e))
        
@cache_monthly
def read_url_cached_monthly(url, userpass=False, return_type='read'):
    log("utils: read_url_cached_monthly")
    try:
        if return_type == 'readlines':
            response = open_url(url, userpass).readlines()
        else:
            response = open_url(url, userpass).read()
        return response
    except Exception,e:
        log('utils: read_url_cached_monthly, Failed!,' + str(e))
  
def open_url(url, userpass=None):
    log("utils: open_url")
    page = ''
    try:
        request = urllib2.Request(url)
        if userpass:
            user, password = userpass.split(':')
            base64string = base64.encodestring('%s:%s' % (user, password))
            request.add_header("Authorization", "Basic %s" % base64string) 
        else:
            # TMDB needs a header to be able to read the data
            if url.startswith("http://api.themoviedb.org"):
                request.add_header("Accept", "application/json")
            else:
                request.add_header('User-Agent','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11')
        page = urllib2.urlopen(request)
        page.close
        return page
    except urllib2.HTTPError, e:
        log("utils: open_url, Failed! " + str(e) + ',' + str(e.fp.read()))
        return page
         
def retrieve_url(url, userpass, dest):
    log("utils: retrieve_url")
    try:
        resource = open_url(url, userpass)
        output = FileAccess.open(dest, 'w')
        output.write(resource.read())  
        output.close()
        return True
    except Exception, e:
        log("utils: retrieve_url, Failed! " + str(e))  
        return False 
        
def anonFTPDownload(filename, DL_LOC):
    log('utils: anonFTPDownload, ' + filename + ' - ' + DL_LOC)
    try:
        ftp = ftplib.FTP("ftp.pseudotvlive.com", "PTVLuser@pseudotvlive.com", "PTVLuser")
        ftp.cwd("/")
        file = FileAccess.open(DL_LOC, 'w')
        ftp.retrbinary('RETR %s' % filename, file.write)
        file.close()
        ftp.quit()
        return True
    except Exception, e:
        log('utils: anonFTPDownload, Failed!! ' + str(e))
        return False
        
@cache_monthly
def get_data(url, data_type ='json'):
    log('utils: get_data, url = ' + url)
    data = []
    try:
        request = urllib2.Request(url)
        # TMDB needs a header to be able to read the data
        if url.startswith("http://api.themoviedb.org"):
            request.add_header("Accept", "application/json")
        req = urllib2.urlopen(request)
        if data_type == 'json':
            data = json.loads(req.read())
            if not data:
                data = 'Empty'
        else:
            data = req.read()
        req.close()
    except Exception,e:
        log("utils: get_data, Failed! " + str(e))
        log(traceback.format_exc(), xbmc.LOGERROR)
        data = 'Empty'
    return data
        
##################
# Zip Tools #
##################

def all(_in, _out, dp=None):
    if dp:
        return allWithProgress(_in, _out, dp)
    return allNoProgress(_in, _out)

def allNoProgress(_in, _out):
    try:
        zin = zipfile.ZipFile(_in, 'r')
        zin.extractall(_out)
    except Exception, e:
        return False
    return True

def allWithProgress(_in, _out, dp):
    zin = zipfile.ZipFile(_in,  'r')
    nFiles = float(len(zin.infolist()))
    count  = 0

    try:
        for item in zin.infolist():
            count += 1
            update = count / nFiles * 100
            dp.update(int(update))
            zin.extract(item, _out)
    except Exception, e:
        return False
    return True 
     
##################
# GUI Tools #
##################

def handle_wait(time_to_wait,header,title,string=None): #*Thanks enen92
    dlg = xbmcgui.DialogProgress()
    dlg.create("PseudoTV Live", header)
    secs=0
    percent=0
    increment = int(100 / time_to_wait)
    cancelled = False
    while secs < time_to_wait:
        secs += 1
        percent = increment*secs
        secs_left = str((time_to_wait - secs))
        if not string:
            remaining_display = "Starts In " + str(secs_left) + " seconds, Cancel Channel Change?" 
        else:
            remaining_display = string
        dlg.update(percent,title,remaining_display)
        xbmc.sleep(1000)
        if (dlg.iscanceled()):
            cancelled = True
            break
    if cancelled == True:
        return False
    else:
        dlg.close()
        return True

def Comingsoon():
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Coming Soon", 1000, THUMB) )

def show_busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialog)')

def hide_busy_dialog():
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    while xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        time.sleep(.1)
        
def Error(header, line1= '', line2= '', line3= ''):
    dlg = xbmcgui.Dialog()
    dlg.ok(header, line1, line2, line3)
    del dlg
    
def showText(heading, text):
    log("utils: showText")
    id = 10147
    xbmc.executebuiltin('ActivateWindow(%d)' % id)
    xbmc.sleep(100)
    win = xbmcgui.Window(id)
    retry = 50
    while (retry > 0):
        try:
            xbmc.sleep(10)
            retry -= 1
            win.getControl(1).setLabel(heading)
            win.getControl(5).setText(text)
            return
        except:
            pass

# General
def infoDialog(message, header=ADDON_NAME, show=True, sound=False, time=1000, icon=THUMB):
    if show:
        try: 
            xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except Exception,e:
            log("utils: infoDialog Failed! " + str(e))
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, THUMB))

# Error
def ErrorNotify(message, header=ADDON_NAME, show=True, sound=False, time=1000, icon=THUMB):
    infoDialog("ERROR: " + message, header, show, sound, time, icon)

# Debug
def DebugNotify(message, header=ADDON_NAME, show=DEBUG, sound=False, time=1000, icon=THUMB):
    infoDialog("DEBUGGING: " + message, header, show, sound, time, icon)

# Optional
def OptNotify(message, header=ADDON_NAME, show=NOTIFY, sound=False, time=1000, icon=THUMB):
    infoDialog(message, header, show, sound, time, icon)
    
def okDialog(str1, str2='', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, str1, str2)

def selectDialog(list, header=ADDON_NAME, autoclose=0):
    if len(list) > 0:
        select = xbmcgui.Dialog().select(header, list, autoclose)
        return select

def yesnoDialog(str1, str2='', header=ADDON_NAME, yes='', no=''):
    answer = xbmcgui.Dialog().yesno(header, str1, str2, '', yes, no)
    return answer
     
def browse(type, heading, shares, mask='', useThumbs=False, treatAsFolder=False, path='', enableMultiple=False):
    retval = xbmcgui.Dialog().browse(type, heading, shares, mask, useThumbs, treatAsFolder, path, enableMultiple)
    return retval
     
##################
# Property Tools #
##################

def getProperty(str):
    return xbmcgui.Window(10000).getProperty(str)

def setProperty(str1, str2):
    xbmcgui.Window(10000).setProperty(str1, str2)

def clearProperty(str):
    xbmcgui.Window(10000).clearProperty(str)
     
##############
# XBMC Tools #
##############
 
def verifyPlayMedia(cmd):
    return True

def verifyPlugin(cmd):
    try:
        plugin = re.compile('plugin://(.+?)/').search(cmd).group(1)
        return xbmc.getCondVisibility('System.HasAddon(%s)' % plugin) == 1
    except:
        pass

    return True

def verifyScript(cmd):
    try:
        script = cmd.split('(', 1)[1].split(',', 1)[0].replace(')', '').replace('"', '')
        script = script.split('/', 1)[0]
        return xbmc.getCondVisibility('System.HasAddon(%s)' % script) == 1

    except:
        pass
    return True

def set_Kodi_JSON(params):
    xbmc.executeJSONRPC('{"jsonrpc": "2.0", %s, "id": 1}' % params)
    
def get_Kodi_JSON(params):
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", %s, "id": 1}' % params)
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    return json.loads(json_query)
    
def isPlugin(plugin):
    if plugin[0:9] == 'plugin://':
        plugin = plugin.replace("plugin://","")
        addon = splitall(plugin)[0]
        log("utils: plugin id = " + addon)
    else:
        addon = plugin
    return xbmc.getCondVisibility('System.HasAddon(%s)' % addon) == 1

def videoIsPlaying():
    return xbmc.getCondVisibility('Player.HasVideo')

def getXBMCVersion():
    log("utils: getXBMCVersion")
    return int((xbmc.getInfoLabel('System.BuildVersion').split('.'))[0])
 
def getPlatform():
    platform = chkPlatform()
    log("utils: getPlatform = " + platform)
    setProperty("PTVL.Platform",platform)
    return platform
    
def chkPlatform():
    log("utils: chkPlatform")
    if xbmc.getCondVisibility('System.Platform.ATV2'):
        REAL_SETTINGS.setSetting('platform', "1")
        return "ATV"
    elif xbmc.getCondVisibility('System.Platform.IOS'):
        REAL_SETTINGS.setSetting('platform', "2")
        return "iOS"
    elif xbmc.getCondVisibility('System.Platform.Xbox'):
        REAL_SETTINGS.setSetting('platform', "5")
        return "XBOX"
    elif xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi'): 
        REAL_SETTINGS.setSetting('platform', "4")
        return "rPi"
    elif xbmc.getCondVisibility('System.Platform.Android'): 
        REAL_SETTINGS.setSetting('platform', "0")
        return "Android"
    elif REAL_SETTINGS.getSetting("platform") == '0': 
        return "Android"
    elif REAL_SETTINGS.getSetting("platform") == '1': 
        return "ATV"
    elif REAL_SETTINGS.getSetting("platform") == "2": 
        return "iOS"
    elif REAL_SETTINGS.getSetting("platform") == "3": 
        return "PowerPC"
    elif REAL_SETTINGS.getSetting("platform") == "4": 
        return "rPi"
    elif REAL_SETTINGS.getSetting("platform") in ["5","7"]: 
        return "APU"
    elif REAL_SETTINGS.getSetting("platform") in ["6","8"]: 
        return "Pro"
    return "Unknown"
     
#####################
# String/File Tools #
#####################
      
def removeNonAscii(string): 
    return "".join(filter(lambda x: ord(x)<128, string))
     
def cleanMovieTitle(title):
    log("utils: cleanMovieTitle")
    title = re.sub('\n|([[].+?[]])|([(].+?[)])|\s(vs|v[.])\s|(:|;|-|"|,|\'|\_|\.|\?)|\s', '', title).lower()
    return title
 
def cleanTVTitle(title):
    log("utils: cleanTVTitle")
    title = re.sub('\n|\s(|[(])(UK|US|AU|\d{4})(|[)])$|\s(vs|v[.])\s|(:|;|-|"|,|\'|\_|\.|\?)|\s', '', title).lower()
    return title  

def cleanEncoding(string):
    string = ''.join(chr(ord(c)) for c in string)
    return ''.join(chr(ord(c)) for c in string).decode('utf8')
             
def normalizeString(string):
    log("utils: normalizeString")
    try:
        try: return string.decode('ascii').encode("utf-8")
        except: pass
        t = ''
        for i in string:
            c = unicodedata.normalize('NFKD',unicode(i,"ISO-8859-1"))
            c = c.encode("ascii","ignore").strip()
            if i == ' ': c = i
            t += c
        return t.encode("utf-8")
    except:
        return string

def encodeString(string):
    return (string.encode('base64')).replace('\n','').replace('\r','').replace('\t','')
    
def decodeString(string):
    return string.decode('base64')
    
def tidy(cmd):
    cmd = cmd.replace('&quot;', '')
    cmd = cmd.replace('&amp;', '&')
    if cmd.startswith('RunScript'):
        cmd = cmd.replace('?content_type=', '&content_type=')
        cmd = re.sub('/&content_type=(.+?)"\)', '")', cmd)
    if cmd.endswith('/")'):
        cmd = cmd.replace('/")', '")')
    if cmd.endswith(')")'):
        cmd = cmd.replace(')")', ')')
    return cmd

def cleanHTML(string):  
    html_parser = HTMLParser.HTMLParser()
    return html_parser.unescape(string)
    
def trim(content, limit, suffix):
    if len(content) <= limit:
        return content
    else:
        return content[:limit].rsplit(' ', 1)[0]+suffix
        
def closest(list, Number):
    aux = []
    for valor in list:
        aux.append(abs(Number-int(valor)))
    return aux.index(min(aux))   
    
def removeStringElem(lst,string=''):
    return ([x for x in lst if x != string])
    
def replaceStringElem(lst,old='',new=''):
    return ([x.replace(old,new) for x in lst])
           
def sorted_nicely(lst): 
    log('utils: sorted_nicely')
    list = set(lst)
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(list, key = alphanum_key)
       
def chunks(l, n):
    n = max(1, n)
    return [l[i:i + n] for i in range(0, len(l), n)]
    
def hashfile(afile, hasher, blocksize=65536):
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    return hasher.digest()
    
def remove_duplicates(values):
    output = []
    seen = set()
    for value in values:
        # If value has not been encountered yet,
        # ... add it to both list and set.
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output
        
def modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)
    
def getSize(file):
    log("getSize")
    if FileAccess.exists(file):
        file = xbmc.translatePath(file)
        try:
            size = os.path.getsize(file)
        except:
            size = 0
        return size
        
def replaceAll(file,searchExp,replaceExp):
    log('utils: script.pseudotv.liveutils: replaceAll')
    for line in fileinput.input(file, inplace=1):
        if searchExp in line:
            line = line.replace(searchExp,replaceExp)
        sys.stdout.write(line)

def splitall(path):
    log("utils: splitall")
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts
    
def replaceXmlEntities(link):
    log('utils: replaceXmlEntities')   
    entities = (
        ("%3A",":"),("%2F","/"),("%3D","="),("%3F","?"),("%26","&"),("%22","\""),("%7B","{"),("%7D",")"),("%2C",","),("%24","$"),("%23","#"),("%40","@"),("&#039;s","'s")
      );
    for entity in entities:
       link = link.replace(entity[0],entity[1]);
    return link;

def convert(s):
    log('utils: convert')       
    try:
        return s.group(0).encode('latin1').decode('utf8')
    except:
        return s.group(0)
        
def copyanything(src, dst):
    try:
        shutil.copytree(src, dst)
    except OSError as exc:
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dst)
        else: 
            raise exception()

def writeCache(theitem, thepath, thefile):
    log("writeCache")  
    now = datetime.datetime.today()

    if not FileAccess.exists(os.path.join(thepath)):
        FileAccess.makedirs(os.path.join(thepath))
    
    thefile = os.path.join(thepath,thefile)
    try:
        fle = FileAccess.open(thefile, "w")
        fle.write("%s\n" % now)
        for item in thelist:
            fle.write("%s\n" % item)
        fle.close()
    except Exception,e:
        log("writeCache, Failed " + str(e))
    
def readCache(thepath, thefile):
    log("readCache") 
    thefile = os.path.join(thepath,thefile)
    
    if FileAccess.exists(thefile):
        try:
            fle = FileAccess.open(thefile, "r")
            theitems = fle.readlines()
            theitems.pop(len(theitems) - 1)#remove last line (empty line)
            theitems.pop(0)#remove first line (datetime)
            fle.close()
            return theitems
        except Exception,e:
            log("readCache, Failed " + str(e))

def Cache_Expired(thepath, thefile, life=31):
    log("Cache_Expired")   
    CacheExpired = False
    thefile = os.path.join(thepath,thefile)
    now = datetime.datetime.today()
    log("Cache_Expired, now = " + str(now))
    
    if FileAccess.exists(thefile):
        try:
            fle = FileAccess.open(thefile, "r")
            cacheline = fle.readlines()
            cacheDate = str(cacheline[0])
            cacheDate = cacheDate.split('.')[0]
            cacheDate = datetime.datetime.strptime(cacheDate, '%Y-%m-%d %H:%M:%S')
            log("Cache_Expired, cacheDate = " + str(cacheDate))
            cacheDateEXP = (cacheDate + datetime.timedelta(days=life))
            log("Cache_Expired, cacheDateEXP = " + str(cacheDateEXP))
            fle.close()  
            
            if now >= cacheDateEXP or len(cacheline) == 2:
                CacheExpired = True         
        except Exception,e:
            log("Cache_Expired, Failed " + str(e))
    else:
        CacheExpired = True    
        
    log("Cache_Expired, CacheExpired = " + str(CacheExpired))
    return CacheExpired
 
def makeSTRM(mediapath):
    log('utils: makeSTRM')            
    if not FileAccess.exists(STRM_CACHE_LOC):
        FileAccess.makedirs(STRM_CACHE_LOC)
    path = (mediapath.encode('base64'))[:16] + '.strm'
    filepath = os.path.join(STRM_CACHE_LOC,path)
    if FileAccess.exists(filepath):
        return filepath
    else:
        fle = FileAccess.open(filepath, "w")
        fle.write("%s" % mediapath)
        fle.close()
        return filepath
         
def Backup(org, bak):
    log('utils: Backup ' + str(org) + ' - ' + str(bak))
    if FileAccess.exists(org):
        if FileAccess.exists(bak):
            try:
                FileAccess.delete(bak)
            except:
                pass
        FileAccess.copy(org, bak)
        infoDialog("Backup Complete")
       
def Restore(bak, org):
    log('utils: Restore ' + str(bak) + ' - ' + str(org))
    if FileAccess.exists(bak):
        if FileAccess.exists(org):
            try:
                FileAccess.delete(org)
            except:
                pass
        xbmcvfs.rename(bak, org)
        infoDialog("Restore Complete, Restarting...")
         
####################
# VideoWindow Hack #
####################
            
def VideoWindow():
    log("utils: VideoWindow, VWPath = " + str(VWPath))
    #Copy VideoWindow Patch file
    try:
        if isLowPower() == True:
            raise Exception()
        else:
            if not FileAccess.exists(VWPath):
                log("utils: VideoWindow, VWPath not found")
                FileAccess.copy(flePath, VWPath)
                if FileAccess.exists(VWPath):
                    log('utils: custom_script.pseudotv.live_9506.xml Copied')
                    xbmc.executebuiltin("ReloadSkin()")
                    VideoWindowPatch()   
                else:
                    raise Exception()
            else:
                log("utils: VideoWindow, VWPath found")
                VideoWindowPatch()  
                
            if FileAccess.exists(VWPath):
                setProperty("PTVL.VideoWindow","true")
    except Exception:
        VideoWindowPatch() 
        VideoWindowUninstall()  
        Error = True
        pass
    
def VideoWindowPatch():
    log("utils: VideoWindowPatch")
    try:
        #Patch dialogseekbar to ignore OSD for PTVL.
        log('utils: VideoWindowPatch Patching ' + ascii(DSPath))
        f = FileAccess.open(DSPath, "r")
        lineLST = f.readlines()            
        f.close()
        
        Ypatch = True
        for i in range(len(lineLST)):
            line = lineLST[i]
            if z in line:
                Ypatch = False
                break
            
        if Ypatch:
            for i in range(len(lineLST)):
                line = lineLST[i]
                if y in line:
                    replaceAll(DSPath,y,z)
                log('utils: dialogseekbar.xml Patched y,z')
    except Exception:
        VideoWindowUninstall()
        pass
   
def VideoWindowUnpatch():
    log("utils: VideoWindowUnpatch")
    try:
        #unpatch seekbar
        f = FileAccess.open(DSPath, "r")
        lineLST = f.readlines()            
        f.close()
        for i in range(len(lineLST)):
            line = lineLST[i]
            if w in line:
                replaceAll(DSPath,w,v)
                log('utils: dialogseekbar.xml UnPatched w,v')
    except Exception:
        Error = True
        pass

def VideoWindowUninstall():
    log('utils: VideoWindowUninstall')
    try:
        FileAccess.delete(VWPath)
        if not FileAccess.exists(VWPath):
            log('utils: custom_script.pseudotv.live_9506.xml Removed')
    except Exception:
        Error = True
        pass
    
######################
# PreStart Functions #
######################
   
def getGithubZip(url, lib, addonpath, MSG):
    log('utils: getGithubZip, url = ' + url)
    # Delete old install package
    try: 
        FileAccess.delete(lib)
        log('utils: deleted old package')
    except: 
        pass  
    try:
        download(url, lib, '')
        log('utils: downloaded new package')
        all(lib,addonpath,'')
        log('utils: extracted new package')
        MSG = MSG + ' Installed'
    except: 
        MSG = MSG + ' Failed to install, Try Again Later'
        pass
        
    xbmc.executebuiltin("XBMC.UpdateLocalAddons()"); 
    infoDialog(MSG)
    
def isContextInstalled():
    context = isPlugin('context.pseudotv.live.export')
    log('utils: isContextInstalled = ' + str(context))
    return context
      
def getContext():  
    log('utils: getContext')
    url='https://github.com/Lunatixz/XBMC_Addons/raw/master/zips/context.pseudotv.live.export/context.pseudotv.live.export-1.0.4.zip'
    name = 'context.pseudotv.live.export.zip' 
    MSG = 'PseudoTV Live Context Export'    
    path = xbmc.translatePath(os.path.join('special://home/addons','packages'))
    addonpath = xbmc.translatePath(os.path.join('special://','home/addons'))
    lib = os.path.join(path,name)
    getGithubZip(url, lib, addonpath, MSG)
    
def isRepoInstalled():
    repo = isPlugin('repository.lunatixz')
    log('utils: isRepoInstalled = ' + str(repo))
    return repo
      
def getRepo():
    log('utils: getRepo')
    url='https://github.com/Lunatixz/XBMC_Addons/raw/master/zips/repository.lunatixz/repository.lunatixz-1.0.zip'
    name = 'repository.lunatixz.zip' 
    MSG = 'Lunatixz Repository Installed'    
    path = xbmc.translatePath(os.path.join('special://home/addons','packages'))
    addonpath = xbmc.translatePath(os.path.join('special://','home/addons'))
    lib = os.path.join(path,name)
    getGithubZip(url, lib, addonpath, MSG)
    
def chkVersion():
    log('utils: chkVersion')
    curver = xbmc.translatePath(os.path.join(ADDON_PATH,'addon.xml'))    
    source = open(curver, mode='r')
    link = source.read()
    source.close()
    match = re.compile('" version="(.+?)" name="PseudoTV Live"').findall(link)
    
    for vernum in match:
        log("utils: Current Version = " + str(vernum))
    try:
        link = open_url('https://raw.githubusercontent.com/Lunatixz/XBMC_Addons/master/script.pseudotv.live/addon.xml').read() 
        link = link.replace('\r','').replace('\n','').replace('\t','').replace('&nbsp;','')
        match = re.compile('" version="(.+?)" name="PseudoTV Live"').findall(link)
    except:
        pass   
        
    if len(match) > 0:
        if vernum != str(match[0]):
            if isRepoInstalled() == False:
                getRepo()

def chkAutoplay():
    log('utils: chkAutoplay')
    fle = xbmc.translatePath("special://profile/guisettings.xml")
    try:
        xml = FileAccess.open(fle, "r")
        dom = parse(xml)
        autoplaynextitem = dom.getElementsByTagName('autoplaynextitem')
        Videoautoplaynextitem  = (autoplaynextitem[0].childNodes[0].nodeValue.lower() == 'true')
        Musicautoplaynextitem  = (autoplaynextitem[1].childNodes[0].nodeValue.lower() == 'true')
        xml.close()
        log('utils: chkAutoplay, Videoautoplaynextitem is ' + str(Videoautoplaynextitem)) 
        log('utils: chkAutoplay, Musicautoplaynextitem is ' + str(Musicautoplaynextitem)) 
        totcnt = Videoautoplaynextitem + Musicautoplaynextitem
        if totcnt > 0:
            okDialog("Its recommended you disable Kodi's"+' "Play the next video/song automatically" ' + "feature found under Kodi's video/playback and music/playback settings.")
        else:
            raise exception()
    except:
        pass
        
def chkSources():
    log("utils: chkSources") 
    hasPVR = False
    hasUPNP = False
    try:
        fle = xbmc.translatePath('special://userdata/sources.xml')
        xml = FileAccess.open(fle, "r")
        dom = parse(xml)
        path = dom.getElementsByTagName('path')
        xml.close()
        for i in range(len(path)):
            line = path[i].childNodes[0].nodeValue.lower()
            if line == 'pvr://':
                hasPVR = True
            elif line == 'upnp://':
                hasUPNP = True
        if hasPVR + hasUPNP == 2:
            return True
    except:
        pass
      
def chkChanges():
    log("utils: chkChanges")
    ComCHK()
    DonCHK()
    
    CURR_BUMPER = REAL_SETTINGS.getSetting('bumpers')
    try:
        CURR_BUMPER = REAL_SETTINGS.getSetting('Last_bumpers')
    except:
        REAL_SETTINGS.setSetting('Last_bumpers', CURR_BUMPER)
    LAST_BUMPER = REAL_SETTINGS.getSetting('Last_bumpers')
    
    if CURR_BUMPER != LAST_BUMPER:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_bumpers', CURR_BUMPER)
        
    CURR_COMMERCIALS = REAL_SETTINGS.getSetting('commercials')
    try:
        CURR_COMMERCIALS = REAL_SETTINGS.getSetting('Last_commercials')
    except:
        REAL_SETTINGS.setSetting('Last_commercials', CURR_COMMERCIALS)
    LAST_COMMERCIALS = REAL_SETTINGS.getSetting('Last_commercials')
    
    if CURR_COMMERCIALS != LAST_COMMERCIALS:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_commercials', CURR_COMMERCIALS)
        
    CURR_TRAILERS = REAL_SETTINGS.getSetting('trailers')
    try:
        CURR_TRAILERS = REAL_SETTINGS.getSetting('Last_trailers')
    except:
        REAL_SETTINGS.setSetting('Last_trailers', CURR_TRAILERS)
    LAST_TRAILERS = REAL_SETTINGS.getSetting('Last_trailers')
    
    if CURR_TRAILERS != LAST_TRAILERS:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_trailers', CURR_TRAILERS)
    
    CURR_ENHANCED_DATA = REAL_SETTINGS.getSetting('EnhancedGuideData')
    try:
        LAST_ENHANCED_DATA = REAL_SETTINGS.getSetting('Last_EnhancedGuideData')
    except:
        REAL_SETTINGS.setSetting('Last_EnhancedGuideData', CURR_ENHANCED_DATA)
    LAST_ENHANCED_DATA = REAL_SETTINGS.getSetting('Last_EnhancedGuideData')
    
    if CURR_ENHANCED_DATA != LAST_ENHANCED_DATA:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_EnhancedGuideData', CURR_ENHANCED_DATA)
        
    CURR_MEDIA_LIMIT = REAL_SETTINGS.getSetting('MEDIA_LIMIT')
    try:
        LAST_MEDIA_LIMIT = REAL_SETTINGS.getSetting('Last_MEDIA_LIMIT')
    except:
        REAL_SETTINGS.setSetting('Last_MEDIA_LIMIT', CURR_MEDIA_LIMIT)
    LAST_MEDIA_LIMIT = REAL_SETTINGS.getSetting('Last_MEDIA_LIMIT')
    
    if CURR_MEDIA_LIMIT != LAST_MEDIA_LIMIT:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_MEDIA_LIMIT', CURR_MEDIA_LIMIT)
              
def chkLowPower(): 
    setProperty("PTVL.LOWPOWER","false") 
    if REAL_SETTINGS.getSetting("Override.LOWPOWER") == "false":
        if getPlatform() in ['PowerPC','ATV','iOS','XBOX','rPi','Android','APU']:
            setProperty("PTVL.LOWPOWER","true") 
            REAL_SETTINGS.setSetting('AT_LIMIT', "0")
            REAL_SETTINGS.setSetting('ThreadMode', "2")
            REAL_SETTINGS.setSetting('EPG.xInfo', "false")
            REAL_SETTINGS.setSetting('EPGTextEnable', "1")
            REAL_SETTINGS.setSetting('SFX_Enabled', "false")
            REAL_SETTINGS.setSetting('EnableSettop', "false")
            REAL_SETTINGS.setSetting('UNAlter_ChanBug', "true")
            REAL_SETTINGS.setSetting('Enable_FindLogo', "false")
            REAL_SETTINGS.setSetting('Disable_Watched', "false")
            REAL_SETTINGS.setSetting('Idle_Screensaver', "false")
            REAL_SETTINGS.setSetting('EnhancedGuideData', "false")
            REAL_SETTINGS.setSetting('sickbeard.enabled', "false")
            REAL_SETTINGS.setSetting('couchpotato.enabled', "false")
            REAL_SETTINGS.setSetting('MEDIA_LIMIT', "1")
            infoDialog("Settings Optimized For Performance")
    else:
        log("utils: chkLowPower Override = True")
    log("utils: chkLowPower = " + getProperty("PTVL.LOWPOWER"))

def isLowPower():
    # log("utils: isLowPower = " + str(getProperty("PTVL.LOWPOWER") == "true"))
    return getProperty("PTVL.LOWPOWER") == "true"
       
def chkAPIS(list):
    try:
        list = list.split('|')
        for i in range(len(list)):
            key = decodeString(list[i])
            hasAPI(key)
    except:
        pass
            
def ClearPlaylists():
    log('utils: ClearPlaylists')
    for i in range(999):
        try:
            FileAccess.delete(CHANNELS_LOC + 'channel_' + str(i) + '.m3u')
        except:
            pass
    infoDialog("Channel Playlists Cleared")
       
                
def ClearCache(type):
    log('utils: ClearCache ' + type)  
    if type == 'Filelist':
        try:    
            daily.delete("%") 
            weekly.delete("%")
            monthly.delete("%")
            shutil.rmtree(REQUESTS_LOC)
        except:
            pass
        REAL_SETTINGS.setSetting('ClearCache', "false")
    elif type == 'Art':
        try:    
            shutil.rmtree(ART_LOC)
            log('utils: Removed ART_LOC')  
            REAL_SETTINGS.setSetting('ClearLiveArtCache', "true") 
            infoDialog("Artwork Folder Cleared")
        except:
            pass
        REAL_SETTINGS.setSetting('ClearLiveArt', "false")
    infoDialog(type + " Cache Cleared")
    
def chkSettings2():   
    log('utils: chkSettings2')
    # check if ptvl shutdown correctly
    try:
        Normal_Shutdown = REAL_SETTINGS.getSetting('Normal_Shutdown') == "true"
    except:
        REAL_SETTINGS.setSetting('Normal_Shutdown', "true")
        Normal_Shutdown = REAL_SETTINGS.getSetting('Normal_Shutdown') == "true"
                 
    if FileAccess.exists(BACKUP_LOC) == False:
        try:
            FileAccess.makedirs(BACKUP_LOC)
        except Exception,e:
            pass
            
    if Normal_Shutdown == False:
        log('utils: chkSettings2, Setting2 Restore') 
        if getSize(SETTINGS_FLE) < SETTINGS_FLE_DEFAULT_SIZE and getSize(SETTINGS_FLE_LASTRUN) > SETTINGS_FLE_DEFAULT_SIZE:
            Restore(SETTINGS_FLE_LASTRUN, SETTINGS_FLE)
    else:
        log('utils: chkSettings2, Setting2 Backup')
        if getSize(SETTINGS_FLE) > SETTINGS_FLE_DEFAULT_SIZE:
            Backup(SETTINGS_FLE, SETTINGS_FLE_LASTRUN)
            if REAL_SETTINGS.getSetting("AutoBackup") == "true":               
                SETTINGS_FLE_BACKUP = os.path.join(BACKUP_LOC, 'settings2.' + (str(datetime.datetime.now()).split('.')[0]).replace(' ','.').replace(':','.') + '.xml')
                Backup(SETTINGS_FLE, SETTINGS_FLE_BACKUP)
    return
    
def backupSettings2():
    log('utils: backupSettings2')
    SETTINGS_FLE_BACKUP = os.path.join(BACKUP_LOC, 'settings2.' + (str(datetime.datetime.now()).split('.')[0]).replace(' ','.').replace(':','.') + '.xml')
    Backup(SETTINGS_FLE, SETTINGS_FLE_BACKUP)

def restoreSettings2():
    log('utils: restoreSettings2')
    dirs,files = xbmcvfs.listdir(BACKUP_LOC)
    dir,file = xbmcvfs.listdir(XMLTV_LOC)
    backuplist = [s.replace('.xml','') for s in files if s.endswith('.xml')]
    if backuplist and len(backuplist) > 0:
        backuplist.reverse()
        select = selectDialog(backuplist, 'Select backup to restore')   
        if select != -1:
            RESTORE_FILE = backuplist[select]+'.xml'
            if dlg.yesno("PseudoTV Live", 'Restoring will remove current channel configurations, Are you sure?'):
                Restore(os.path.join(BACKUP_LOC, RESTORE_FILE, SETTINGS_FLE))
                return infoDialog("Restore Complete")
    else:
        return infoDialog("No Backups found")
        
def purgeSettings2():
    log('utils: purgeSettings2')
    if dlg.yesno("PseudoTV Live", 'Are you sure you want to remove all previous backups?'):       
        dirs,files = xbmcvfs.listdir(BACKUP_LOC)
        for i in range(len(files)):
            try:
                FileAccess.delete(os.path.join(BACKUP_LOC,files[i]))
            except:
                pass
        infoDialog("Backup Purge Complete")

def hasVersionChanged(__version__): 
    log('utils: hasVersionChanged = ' + __version__)   
    try:
        PTVL_Version = REAL_SETTINGS.getSetting("PTVL_Version")
        if not PTVL_Version:
            raise exception()
    except:
        REAL_SETTINGS.setSetting("PTVL_Version", __version__)
        PTVL_Version = REAL_SETTINGS.getSetting("PTVL_Version") 
    
    if PTVL_Version != __version__:
        REAL_SETTINGS.setSetting("PTVL_Version", __version__)
        return True
    else:
        return False
        
def HandleUpgrade():
    log('utils: HandleUpgrade') 
    # Remove m3u playlists
    # ClearPlaylists()
    
    # Force Channel rebuild
    # REAL_SETTINGS.setSetting('ForceChannelReset', 'true') 
             
    # Install PTVL Isengard Context Export
    if getXBMCVersion() > 14 and isContextInstalled() == False:
        getContext()
        
    # Check if autoplay is enabled
    chkAutoplay()
    
    # Call showChangeLog like this to workaround bug in openElec, *Thanks spoyser
    xbmc.executebuiltin("RunScript(" + ADDON_PATH + "/utilities.py,-showChangelog)")
    
def preStart(): 
    log('utils: preStart')
    # Optimize settings based on sys.platform
    chkLowPower()
    
    if isDebug() == True:
        if yesnoDialog('Its recommended you disable debug logging for standard use','Disable Debugging?') == True:
            REAL_SETTINGS.setSetting('enable_Debug', "false")

    # VideoWindow Patch.
    VideoWindow()
    
    # Clear filelist Caches    
    if REAL_SETTINGS.getSetting("ClearCache") == "true":
        ClearCache('Filelist')
        
    # Clear Artwork Folders
    if REAL_SETTINGS.getSetting("ClearLiveArt") == "true":
        ClearCache('Art')
            
    # Backup/Restore settings2
    chkSettings2()
    
    return
        
##############
# PTVL Tools #
##############

def PlaylistLimit():  
    if getPlatform() == 'Windows':
        Playlist_Limit = FILELIST_LIMIT[2]
    elif isLowPower() != True:
        Playlist_Limit = FILELIST_LIMIT[1]
    else:
        Playlist_Limit = FILELIST_LIMIT[0]
    log('utils: PlaylistLimit = ' + str(Playlist_Limit))
    return Playlist_Limit

def isDon():
    return getProperty("Verified_Donor") == "true"
    
def isCom():
    return getProperty("Verified_Community") == "true"
        
def ComCHK():
    log('utils: ComCHK')      
    # Community users are required to supply gmail info in-order to use the community submission tool, SEE DISCLAIMER!!
    # Submission tool uses emails to submit channel configurations, which are then added to a public (github) list: https://github.com/PseudoTV/PseudoTV_Lists
    # Community lists includes: Youtube, Vimeo, RSS, Smartplaylists, LiveTV (legal feeds ONLY!), InternetTV (legal feeds ONLY!) and User installed and Kodi repository plugins (see isKodiRepo, isPlugin).
    if REAL_SETTINGS.getSetting("Community_Enabled") == "true":
        if REAL_SETTINGS.getSetting("Community_Verified") != "1": 
            REAL_SETTINGS.setSetting("Community_Verified", "1")
            REAL_SETTINGS.setSetting("AT_Community","true")
            infoDialog("Community List Activated")
        setProperty("Verified_Community", 'true')
    else:
        if REAL_SETTINGS.getSetting("Community_Verified") != "0": 
            REAL_SETTINGS.setSetting("Community_Verified", "0")
            REAL_SETTINGS.setSetting("AT_Community","false")
        setProperty("Verified_Community", 'false')
       
def DonCHK():
    log('utils: DonCHK')     
    # Access tv meta, commercials, adverts and various legal custom videos from a private server.
    if REAL_SETTINGS.getSetting("Donor_Enabled") == "true": 
        try:
            list = getDonlist('ce.ini', test=True)
            if len(list) == 0:
                log('utils: DonCHK = Failed')  
                raise Exception()
            log('utils: DonCHK = Passed')  
            if REAL_SETTINGS.getSetting("Donor_Verified") != "1": 
                REAL_SETTINGS.setSetting("Donor_Verified", "1")
                REAL_SETTINGS.setSetting("AT_Donor", "true")
                REAL_SETTINGS.setSetting("COM_Donor", "true")
                infoDialog("Donor Access Activated")
            setProperty("Verified_Donor", 'true')
        except:
            DonFailed()
    else:
        DonFailed()
           
def DonFailed():
    log('utils: DonFailed')    
    if REAL_SETTINGS.getSetting("Donor_Verified") != "0": 
        REAL_SETTINGS.setSetting("Donor_Verified", "0")
        REAL_SETTINGS.setSetting("AT_Donor", "false")
        REAL_SETTINGS.setSetting("COM_Donor", "false")
    setProperty("Verified_Donor", 'false')
    
def getDonlist(list, test=False):
    log('utils: getDonlist, test = ' + str(test))
    nlist = []
    if test:
        list = open_url(PTVLURL + list, UPASS).readlines()
    else:
        list = read_url_cached(PTVLURL + list, UPASS, return_type='readlines')
    for i in range(len(list)):
        try:
            nline = (list[i]).replace('\r\n','')
            nlist.append(nline)
        except:
            pass
    return nlist

def getTitleYear(showtitle, showyear=0):  
    # extract year from showtitle, merge then return
    try:
        labelshowtitle = re.compile('(.+?) [(](\d{4})[)]$').findall(showtitle)
        title = labelshowtitle[0][0]
        year = int(labelshowtitle[0][1])
    except Exception,e:
        try:
            year = int(((showtitle.split(' ('))[1]).replace(')',''))
            title = ((showtitle.split('('))[0])
        except Exception,e:
            if showyear != 0:
                showtitle = showtitle + ' ('+str(showyear)+')'
                year, title, showtitle = getTitleYear(showtitle, showyear)
            else:
                title = showtitle
                year = 0
    if year == 0 and int(showyear) !=0:
        year = int(showyear)
    if year != 0 and '(' not in title:
        showtitle = title + ' ('+str(year)+')' 
    log("utils: getTitleYear, return " + str(year) +', '+ title +', '+ showtitle) 
    return year, title, showtitle

def splitDBID(dbid):
    try:
        epid = dbid.split(':')[1]
        dbid = dbid.split(':')[0]
    except:
        epid = '0'
    log('utils: splitDBID, dbid = '+dbid+', epid = '+epid)
    return dbid, epid
    
def getMpath(mediapath):
    log('utils: getMpath')
    try:
        if mediapath[0:5] == 'stack':
            smpath = (mediapath.split(' , ')[0]).replace('stack://','').replace('rar://','')
            mpath = (os.path.split(smpath)[0]) + '/'
        elif mediapath[0:6] == 'plugin':
            mpath = 'plugin://' + mediapath.split('/')[2] + '/'
        elif mediapath[0:4] == 'upnp':
            mpath = 'upnp://' + mediapath.split('/')[2] + '/'
        else:
            mpath = (os.path.split(mediapath)[0]) + '/'
    except Exception,e:
        mpath = mediapath
    return mpath

def EXTtype(arttype): 
    arttype = arttype.replace('.png','').replace('.jpg','')
    JPG = ['banner', 'fanart', 'folder', 'landscape', 'poster']
    PNG = ['character', 'clearart', 'logo', 'disc']
    if arttype in JPG:
        arttypeEXT = (arttype + '.jpg')
    else:
        arttypeEXT = (arttype + '.png')
    log('utils: EXTtype = ' + str(arttypeEXT))
    return arttypeEXT

def isDebug():
    return REAL_SETTINGS.getSetting('enable_Debug') == "true"

def SyncXMLTV(force=False):
    try:
        if REAL_SETTINGS.getSetting("SyncXMLTV_Enabled") == "true" and isDon() == True: 
            SyncXMLTVtimer = threading.Timer(0.1, SyncXMLTV_NEW, [force])
            SyncXMLTVtimer.name = "SyncXMLTVtimer"     
            if SyncXMLTVtimer.isAlive():
                SyncXMLTVtimer.cancel()
            SyncXMLTVtimer.start()
    except Exception,e:
        log('SyncXMLTV_NEW, Failed!, ' + str(e))
        pass  
        
def SyncXMLTV_NEW(force=False):
    log('utils: SyncXMLTV_NEW, force = ' + str(force))
    now  = datetime.datetime.today()
    try:
        try:
            SyncPTV_LastRun = REAL_SETTINGS.getSetting('SyncPTV_NextRun')
            if not SyncPTV_LastRun or FileAccess.exists(PTVLXML) == False or force == True:
                raise exception()
        except:
            REAL_SETTINGS.setSetting("SyncPTV_NextRun","1970-01-01 23:59:00.000000")
            SyncPTV_LastRun = REAL_SETTINGS.getSetting('SyncPTV_NextRun')

        try:
            SyncPTV = datetime.datetime.strptime(SyncPTV_LastRun, "%Y-%m-%d %H:%M:%S.%f")
        except:
            SyncPTV = datetime.datetime.strptime("1970-01-01 23:59:00.000000", "%Y-%m-%d %H:%M:%S.%f")
            
        if now > SyncPTV:         
            #Remove old file before download
            if FileAccess.exists(PTVLXML):
                try:
                    FileAccess.delete(PTVLXML)
                    log('utils: SyncXMLTV, Removed old PTVLXML')
                except:
                    log('utils: SyncXMLTV, Removing old PTVLXML Failed!')
                    
            if retrieve_url(PTVLXMLURL, UPASS, PTVLXMLZIP):
                if FileAccess.exists(PTVLXMLZIP):
                    all(PTVLXMLZIP,XMLTV_CACHE_LOC)
                    try:
                        FileAccess.delete(PTVLXMLZIP)
                        log('utils: SyncXMLTV, Removed PTVLXMLZIP')
                    except:
                        log('utils: SyncXMLTV, Removing PTVLXMLZIP Failed!')
                
                if FileAccess.exists(PTVLXML):
                    log('utils: SyncXMLTV, ptvlguide.xml download successful!')  
                    infoDialog("Guidedata Update Complete")
                    SyncPTV_NextRun = ((now + datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S.%f"))
                    log('utils: SyncXMLTV, Now = ' + str(now) + ', SyncPTV_NextRun = ' + str(SyncPTV_NextRun))
                    REAL_SETTINGS.setSetting("SyncPTV_NextRun",str(SyncPTV_NextRun))
                    REAL_SETTINGS.setSetting('PTVLXML_FORCE', 'false')
    except Exception,e:
        log("utils: SyncXMLTV_NEW Failed!" + str(e))
        
def help(chtype):
    log('utils: help, ' + chtype)
    HelpBaseURL = 'https://raw.githubusercontent.com/Lunatixz/XBMC_Addons/master/script.pseudotv.live/resources/help/help_'
    type = (chtype).replace('None','General')
    URL = HelpBaseURL + (type.lower()).replace(' ','%20')
    log("utils: help URL = " + URL)
    title = type + ' Configuration Help'
    f = open_url(URL)
    text = f.read()
    showText(title, text)
    
def listXMLTV():
    log("utils: listXMLTV")
    xmltvLst = []   
    EXxmltvLst = ['pvr','scheduledirect (Coming Soon)','zap2it (Coming Soon)']
    dirs,files = xbmcvfs.listdir(XMLTV_CACHE_LOC)
    dir,file = xbmcvfs.listdir(XMLTV_LOC)
    xmltvcacheLst = [s.replace('.xml','') for s in files if s.endswith('.xml')] + EXxmltvLst
    xmltvLst = sorted_nicely([s.replace('.xml','') for s in file if s.endswith('.xml')] + xmltvcacheLst)
    select = selectDialog(xmltvLst, 'Select xmltv file')

    if select != -1:
        return xmltvLst[select]        
        
def xmltvFile(setting3):
    log("utils: xmltvFile")                
    if setting3[0:4] == 'http' or setting3.lower() == 'pvr' or setting3.lower() == 'scheduledirect' or setting3.lower() == 'zap2it':
        xmltvFle = setting3
    elif setting3.lower() == 'ptvlguide':
        xmltvFle = PTVLXML
    else:
        xmltvFle = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('xmltvLOC'), str(setting3) +'.xml'))
    return xmltvFle

def getRSSFeed(genre):
    log("utils: getRSSFeed, genre = " + genre)
    feed = ''
    if genre.lower() == 'news':
        feed = 'http://feeds.bbci.co.uk/news/rss.xml'
    # todo parse git list pair rss by genre
    parseFeed(feed)
    
def parseFeed(link):
    log("utils: parseFeed")
    # RSSlst = ''
    # try:
        # feed = feedparser.parse(link)
        # header = (feed['feed']['title'])
        # title = feed['entries'][1].title
        # description =  feed['entries'][1].summary,
        # RSSlst = '[B]'+ header + "[/B]: "
        # for i in range(0,len(feed['entries'])):
            # RSSlst += ('[B]'+replaceXmlEntities(feed['entries'][i].title) + "[/B] - " + replaceXmlEntities((feed['entries'][i].summary).split('<')[0]))
        # setProperty("RSS.FEED", utf(RSSlst))
    # except Exception,e:
        # log("getRSSFeed Failed!" + str(e))
        # pass

def correctYoutubeSetting2(setting2):
    setting2 = setting2.replace('Multi Playlist','7').replace('Multi Channel','8').replace('Raw gdata','9')
    setting2 = setting2.replace('User Favorites','4').replace('Search Query','5').replace('User Subscription','3')
    setting2 = setting2.replace('Seasonal','31').replace('Channel','1').replace('Playlist','2')
    return setting2
     
def purgeGarbage(): 
    try:
        # only purge when not building channel lists.
        if isBackgroundLoading() == False:
            # threshold = gc.get_threshold()
            # log("utils: purgeGarbage, Garbage collection thresholds: %s" % (str(threshold)))
            collected = gc.collect()
            log("utils: purgeGarbage, Garbage collector: collected %d objects." % (collected))
            log("utils: purgeGarbage, Garbage collector: Cleaning")
            gc.collect()
            collected = gc.collect()
            log("utils: purgeGarbage, Garbage collector: %d objects left." % (collected))
            log("utils: purgeGarbage, Garbage collector: Finished")
    except Exception,e:
        log("purgeGarbage Failed!" + str(e))
        
def isScanningVideo():
    return xbmc.getCondVisibility("Library.IsScanningVideo")
    
def isScanningMusic():
    return xbmc.getCondVisibility("Library.IsScanningMusic")
    
def updateLibrary(type='video', path=''):
    xbmc.executebuiltin('UpdateLibrary(%s,[%s])' %(type, path))
    
def isBackgroundLoading():
    return getProperty("PTVL.BackgroundLoading") == 'true'