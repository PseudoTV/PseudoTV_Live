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

# Commoncache plugin import
try:
    import StorageServer
except Exception,e:
    import storageserverdummy as StorageServer

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

# Settings2 filepaths
settingFileAccess = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.xml'))
nsettingFileAccess = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.lastrun.xml'))
atsettingFileAccess = xbmc.translatePath(os.path.join(BACKUP_LOC, 'settings2.pretune.xml'))
bksettingFileAccess = os.path.join(BACKUP_LOC, 'settings2.' + (str(datetime.datetime.now()).split('.')[0]).replace(' ','.').replace(':','.') + '.xml')

# Videowindow filepaths
Path = xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', '1080i'))
flePath = xbmc.translatePath(os.path.join(Path, 'custom_script.pseudotv.live_9506.xml'))
PTVL_SKIN_WINDOW_FLE = ['script.pseudotv.live.EPG.xml','script.pseudotv.live.OnDemand.xml','script.pseudotv.live.DVR.xml','script.pseudotv.live.Apps.xml']     
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
    log("utils: fillGithubItems, url = " + url + ', ext = ' + ext)
    Sortlist = []
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
        Sortlist = sorted_nicely(list) 
        log("utils: fillGithubItems, found %s items" % str(len(Sortlist)))
    except Exception,e:
        log("utils: fillGithubItems, Failed! " + str(e))
        log(traceback.format_exc(), xbmc.LOGERROR)
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
            return GrabLogo(url, chname)
    if chtype in [0,1,2,3,4,5,12,13,14]:
        log("utils: FindLogo_Thread, findGithubLogo")
        url = findGithubLogo(chname)
        if url:
            return GrabLogo(url, chname) 
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
            return GrabLogo(url, chname) 
  
def FindLogo(chtype, chname, mediapath=None):
    log("utils: FindLogo")
    try:
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
        OPTIONS = ['PTVL',str(ADDON_VERSION),str(VISITOR)]
        
        if getProperty("Verified_Donor") == "True":
            OPTIONS = OPTIONS + ['Donor:'+(REAL_SETTINGS.getSetting('Donor_UP')).split(':')[0]]
        else:
            OPTIONS = OPTIONS+ ['FreeUser']
        
        if getProperty("Verified_Community") == "True":
            OPTIONS = OPTIONS + ['Com:'+REAL_SETTINGS.getSetting('Gmail_User')]
        else:
            OPTIONS = OPTIONS+ ['Com:False']
                    
        if isPlugin('context.pseudotv.live.export'):
            OPTIONS = OPTIONS + ['CM:True']
        else:
            OPTIONS = OPTIONS + ['CM:False']
            
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
            raise exception()
    except:
        UpdateRSS_LastRun = "1970-01-01 23:59:00.000000"
        setProperty("UpdateRSS_NextRun",UpdateRSS_LastRun)
    try:
        SyncUpdateRSS = datetime.datetime.strptime(UpdateRSS_LastRun, "%Y-%m-%d %H:%M:%S.%f")
    except:
        UpdateRSS_LastRun = "1970-01-01 23:59:00.000000"
        SyncUpdateRSS = datetime.datetime.strptime(UpdateRSS_LastRun, "%Y-%m-%d %H:%M:%S.%f")
    # log('utils: UpdateRSS, Now = ' + str(now) + ', UpdateRSS_NextRun = ' + str(UpdateRSS_LastRun))
    
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
        
@cache_weekly
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
  
def open_url(url, userpass=None):
    log("utils: open_url, url = " + str(url))
    try:
        request = urllib2.Request(url)
        if userpass:
            userpass = userpass.split(':')
            base64string = base64.encodestring('%s:%s' % (userpass[0], userpass[1])).replace('\n', '')
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
    log('utils: get_data')
    data = []
    try:
        req = read_url_cached(url)
        if data_type == 'json':
            data = json.loads(req)
            if not data:
                data = 'Empty'
        else:
            data = req
    except HTTPError, e:
        if e.code == 400:
            raise HTTP400Error(url)
        elif e.code == 404:
            raise HTTP404Error(url)
        elif e.code == 503:
            raise HTTP503Error(url)
        else:
            raise DownloadError(str(e))
    except URLError:
        raise HTTPTimeout(url)
    except socket.timeout, e:
        raise HTTPTimeout(url)
    except:
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

def handle_wait(time_to_wait,header,title): #*Thanks enen92
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
        remaining_display = "Starts In " + str(secs_left) + " seconds, Cancel Channel Change?" 
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

def infoDialog(str, header=ADDON_NAME, time=4000):
    try: xbmcgui.Dialog().notification(header, str, THUMB, time, sound=False)
    except: xbmc.executebuiltin("Notification(%s,%s, %s, %s)" % (header, str, time, THUMB))

def stdNotify(message, time=4000, show=NOTIFY, sound=False, icon=THUMB, header=ADDON_NAME):
    if show == True:
        xbmcgui.Dialog().notification(heading=header, message=message, icon=icon, time=time, sound=sound)

def DebugNotify(string):
    if DEBUG:
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "DEBUGGING: " + string, 1000, THUMB))
    
def okDialog(str1, str2='', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, str1, str2)

def selectDialog(list, header=ADDON_NAME, autoclose=0):
    if len(list) > 0:
        select = xbmcgui.Dialog().select(header, list, autoclose)
        return select

def yesnoDialog(str1, str2='', header=ADDON_NAME, str3='', str4=''):
    answer = xbmcgui.Dialog().yesno(header, str1, str2, '', str4, str3)
    return answer
     
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
    log("utils: getPlatform")
    if xbmc.getCondVisibility('system.platform.osx'):
        return "OSX"
    elif xbmc.getCondVisibility('system.platform.atv2'):
        REAL_SETTINGS.setSetting('os', "4")
        return "ATV2"
    elif xbmc.getCondVisibility('system.platform.ios'):
        REAL_SETTINGS.setSetting('os', "5")
        return "iOS"
    elif xbmc.getCondVisibility('system.platform.windows'):
        REAL_SETTINGS.setSetting('os', "11")
        return "Windows"
    elif xbmc.getCondVisibility('system.platform.darwin'):
        return "Darwin"
    elif xbmc.getCondVisibility('system.platform.linux'):
        return "Linux"
    elif xbmc.getCondVisibility('system.platform.linux.raspberryPi'): 
        REAL_SETTINGS.setSetting('os', "10")
        return "rPi"
    elif xbmc.getCondVisibility('system.platform.android'): 
        return "Android"
    elif REAL_SETTINGS.getSetting("os") in ['0','1']: 
        return "Android"
    elif REAL_SETTINGS.getSetting("os") in ['2','3','4']: 
        return "ATV2"
    elif REAL_SETTINGS.getSetting("os") == "5": 
        return "iOS"
    elif REAL_SETTINGS.getSetting("os") in ['6','7']: 
        return "Linux"
    elif REAL_SETTINGS.getSetting("os") in ['8','9']: 
        return "OSX"
    elif REAL_SETTINGS.getSetting("os") == "10": 
        return "rPi"
    elif REAL_SETTINGS.getSetting("os") == "11": 
        return "Windows"
    return "Unknown"
     
#####################
# String/File Tools #
#####################
            
def normalizeString(string):
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
    if FileAccess.exists(file):
        fileobject = FileAccess.open(file, "r")
        fileobject.seek(0,2) # move the cursor to the end of the file
        size = fileobject.tell()
        fileobject.close()
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
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Backup Complete", 1000, THUMB) )
       
def Restore(bak, org):
    log('utils: Restore ' + str(bak) + ' - ' + str(org))
    if FileAccess.exists(bak):
        if FileAccess.exists(org):
            try:
                FileAccess.delete(org)
            except:
                pass
        xbmcvfs.rename(bak, org)
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Restore Complete, Restarting...", 1000, THUMB) )
    
##############
# PTVL Tools #
##############

def isDon():
    val = REAL_SETTINGS.getSetting("Verified_Donor") == "true"
    setProperty("Verified_Donor", str(val))
    log('utils: isDon = ' + str(val))
    return val
    
def isCom():
    val = REAL_SETTINGS.getSetting("Verified_Community") == "true"
    setProperty("Verified_Community", str(val))
    log('utils: isCom = ' + str(val))
    return val
        
def DonCHK():
    # Access tv meta, commercials, adverts and various legal custom videos from a private server.
    if REAL_SETTINGS.getSetting("Donor_Enabled") == "true" and REAL_SETTINGS.getSetting("Donor_UP") != 'Username:Password': 
        try:
            open_url(PTVLURL + 'ce.ini', UPASS).read()
            if REAL_SETTINGS.getSetting("Donor_Verified") != "1": 
                REAL_SETTINGS.setSetting("AT_Donor", "true")
                REAL_SETTINGS.setSetting("COM_Donor", "true")
                REAL_SETTINGS.setSetting("Verified_Donor", "true")
                REAL_SETTINGS.setSetting("Donor_Verified", "1")
                xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live","Donor Access Activated", 1000, THUMB) )
        except:
            DonFailed()
    else:
        DonFailed()
           
def ComCHK():
    # Community users are required to supply gmail info in-order to use the community submission tool, SEE DISCLAIMER!!
    # Submission tool uses emails to submit channel configurations, which are then added to a public (github) list: https://github.com/PseudoTV/PseudoTV_Lists
    # Community lists includes: Youtube, Vimeo, RSS, Smartplaylists, LiveTV (legal feeds ONLY!), InternetTV (legal feeds ONLY!) and User installed and Kodi repository plugins (see isKodiRepo, isPlugin).
    if REAL_SETTINGS.getSetting("Community_Enabled") == "true" and REAL_SETTINGS.getSetting("Gmail_User") != 'User@gmail.com':
        if REAL_SETTINGS.getSetting("Community_Verified") != "1": 
            REAL_SETTINGS.setSetting("AT_Community","true")
            REAL_SETTINGS.setSetting("Verified_Community", "true")
            REAL_SETTINGS.setSetting("Community_Verified", "1")
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live","Community List Activated", 1000, THUMB) )
    else:
        if REAL_SETTINGS.getSetting("Community_Verified") != "0": 
            REAL_SETTINGS.setSetting("AT_Community","false")
            REAL_SETTINGS.setSetting("Verified_Community", "false")
            REAL_SETTINGS.setSetting("Community_Verified", "0")
       
def DonFailed():
    if REAL_SETTINGS.getSetting("Donor_Verified") != "0": 
        REAL_SETTINGS.setSetting("AT_Donor", "false")
        REAL_SETTINGS.setSetting("COM_Donor", "false")
        REAL_SETTINGS.setSetting("Verified_Donor", "false")
        REAL_SETTINGS.setSetting("Donor_Verified", "0")
     
def getDonlist(list):
    log("getDonlist")  
    nlist = []
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
    log('utils: splitDBID')
    try:
        epid = dbid.split(':')[1]
        dbid = dbid.split(':')[0]
    except:
        epid = '0'
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
    log('utils: SyncXMLTV, force = ' + str(force))
    try:
        SyncXMLTVthread = threading.Timer(0.5, SyncXMLTV_Thread, [force])
        SyncXMLTVthread.name = "SyncXMLTVthread"
        if SyncXMLTVthread.isAlive():
            SyncXMLTVthread.cancel()      
        SyncXMLTVthread.start()
    except Exception,e:
        log('utils: SyncXMLTV, Failed!,' + str(e))
        pass   
         
def SyncXMLTV_Thread(force=False):
    log('utils: SyncXMLTV_Thread, force = ' + str(force))
    now  = datetime.datetime.today()
    try:
        SyncPTV_LastRun = REAL_SETTINGS.getSetting('SyncPTV_NextRun')
        if not SyncPTV_LastRun or FileAccess.exists(PTVLXML) == False or force == True:
            raise exception()
    except:
        SyncPTV_LastRun = "1970-01-01 23:59:00.000000"
        REAL_SETTINGS.setSetting("SyncPTV_NextRun",SyncPTV_LastRun)

    try:
        SyncPTV = datetime.datetime.strptime(SyncPTV_LastRun, "%Y-%m-%d %H:%M:%S.%f")
    except:
        SyncPTV_LastRun = "1970-01-01 23:59:00.000000"
        SyncPTV = datetime.datetime.strptime(SyncPTV_LastRun, "%Y-%m-%d %H:%M:%S.%f")
    
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
                xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live","Guidedata Update Complete", 1000, THUMB) )  
                SyncPTV_NextRun = ((now + datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S.%f"))
                log('utils: SyncXMLTV, Now = ' + str(now) + ', SyncPTV_NextRun = ' + str(SyncPTV_NextRun))
                REAL_SETTINGS.setSetting("SyncPTV_NextRun",str(SyncPTV_NextRun))
                REAL_SETTINGS.setSetting('PTVLXML_FORCE', 'false')

def help(chtype):
    log('utils: help, ' + chtype)
    HelpBaseURL = 'http://raw.github.com/PseudoTV/XBMC_Addons/master/script.pseudotv.live/resources/help/help_'
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
    
####################
# VideoWindow Hack #
####################
            
def VideoWindow():
    log("utils: VideoWindow, VWPath = " + str(VWPath))
    #Copy VideoWindow Patch file
    try:
        if getProperty("PseudoTVRunning") != "True":
            if not FileAccess.exists(VWPath):
                log("utils: VideoWindow, VWPath not found")
                FileAccess.copy(flePath, VWPath)
                if FileAccess.exists(VWPath):
                    log('utils: custom_script.pseudotv.live_9506.xml Copied')
                    xbmc.executebuiltin("ReloadSkin()")
                    VideoWindowPatch()   
                else:
                    raise exception()
            else:
                log("utils: VideoWindow, VWPath found")
                VideoWindowPatch()  
                
            if FileAccess.exists(VWPath):
                setProperty("PTVL.VideoWindow","true")
    except Exception:
        VideoWindowUninstall()
        VideoWindowUnpatch()
        Error = True
        pass
    
def VideoWindowPatch():
    log("utils: VideoWindowPatch")
    try:
        for n in range(len(PTVL_SKIN_WINDOW_FLE)):
            PTVL_SKIN_SELECT_FLE = xbmc.translatePath(os.path.join(PTVL_SKIN_SELECT, PTVL_SKIN_WINDOW_FLE[n]))
            log('utils: VideoWindowPatch Patching ' + ascii(PTVL_SKIN_SELECT_FLE))
            #Patch Videowindow, by un-commenting code in epg.xml 
            f = FileAccess.open(PTVL_SKIN_SELECT_FLE, "r")
            linesLST = f.readlines()  
            f.close()
            
            for i in range(len(linesLST)):
                line = linesLST[i]
                if line in b:
                    replaceAll(PTVL_SKIN_SELECT_FLE,b,a)        
                    log('utils: '+PTVL_SKIN_WINDOW_FLE[n]+' Patched b,a')
                elif line in d:
                    replaceAll(PTVL_SKIN_SELECT_FLE,d,c)           
                    log('utils: '+PTVL_SKIN_WINDOW_FLE[n]+' Patched d,c') 
                    
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
        for n in range(len(PTVL_SKIN_WINDOW_FLE)):
            PTVL_SKIN_SELECT_FLE = xbmc.translatePath(os.path.join(PTVL_SKIN_SELECT, PTVL_SKIN_WINDOW_FLE[n]))
            #unpatch videowindow
            f = FileAccess.open(PTVL_SKIN_SELECT_FLE, "r")
            linesLST = f.readlines()    
            f.close()
            for i in range(len(linesLST)):
                lines = linesLST[i]
                if lines in a:
                    replaceAll(PTVL_SKIN_SELECT_FLE,a,b)
                    log('utils: '+PTVL_SKIN_WINDOW_FLE[n]+' UnPatched a,b')
                elif lines in c:
                    replaceAll(PTVL_SKIN_SELECT_FLE,c,d)          
                    log('utils: '+PTVL_SKIN_WINDOW_FLE[n]+' UnPatched c,d')
                
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

def getRepo():
    log('utils: getRepo')
    url='https://github.com/Lunatixz/XBMC_Addons/raw/master/zips/repository.lunatixz/repository.lunatixz-1.0.zip'
    name = 'repository.lunatixz.zip' 
    MSG = 'Lunatixz Repository Installed'    
    path = xbmc.translatePath(os.path.join('special://home/addons','packages'))
    addonpath = xbmc.translatePath(os.path.join('special://','home/addons'))
    lib = os.path.join(path,name)
    log('utils: URL = ' + url)
    
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
    except: 
        MSG = 'Failed to install Lunatixz Repository, Try Again Later'
        pass
        
    xbmc.executebuiltin("XBMC.UpdateLocalAddons()"); 
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", MSG, 1000, THUMB) )
    return
 
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
            if not isPlugin('repository.lunatixz'):
                dialog = xbmcgui.Dialog()
                confirm = xbmcgui.Dialog().yesno('[B]PseudoTV Live Update Available![/B]', "Your version is outdated." ,'The current available version is '+str(match[0]),'Would you like to install the PseudoTV Live repository to stay updated?',"Cancel","Install")
                if confirm:
                    getRepo()
            # else:
                # get_Kodi_JSON('"method":"Addons.SetAddonEnabled","params":{"addonid":"repository.lunatixz","enabled":true}')

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
    # todo add bcts
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
        if getPlatform() in ['ATV2','iOS','rPi','Android']:
            setProperty("PTVL.LOWPOWER","true") 
            REAL_SETTINGS.setSetting('AT_LIMIT', "25")
            REAL_SETTINGS.setSetting('EPG.xInfo', "false")
            REAL_SETTINGS.setSetting('HideClips', "false")
            REAL_SETTINGS.setSetting('EPGTextEnable', "1")
            REAL_SETTINGS.setSetting('SFX_Enabled', "false")
            REAL_SETTINGS.setSetting('Enable_FindLogo', "false")
            REAL_SETTINGS.setSetting('Disable_Watched', "false")
            REAL_SETTINGS.setSetting('Idle_Screensaver', "false")
            REAL_SETTINGS.setSetting('EnhancedGuideData', "false")
            if MEDIA_LIMIT > 250:
                REAL_SETTINGS.setSetting('MEDIA_LIMIT', "3")
            if NOTIFY == True:
                xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Settings Optimized For Performance", 1000, THUMB) )
    log("utils: chkLowPower = " + getProperty("PTVL.LOWPOWER"))

def isLowPower():
    return getProperty("PTVL.LOWPOWER") == "true"
             
def ClearPlaylists():
    log('utils: ClearPlaylists')
    for i in range(999):
        try:
            FileAccess.delete(CHANNELS_LOC + 'channel_' + str(i) + '.m3u')
        except:
            pass
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", 'Channel Playlists Cleared', 1000, THUMB) )
    return   
                
def ClearCache(type):
    log('utils: ClearCache ' + type)  
    if type == 'Filelist':
        daily.delete("%") 
        weekly.delete("%")
        monthly.delete("%")
        REAL_SETTINGS.setSetting('ClearCache', "false")
    elif type == 'Art':
        try:    
            shutil.rmtree(ART_LOC)
            log('utils: Removed ART_LOC')  
            REAL_SETTINGS.setSetting('ClearLiveArtCache', "true") 
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Artwork Folder Cleared", 1000, THUMB) )
        except:
            pass
        REAL_SETTINGS.setSetting('ClearLiveArt', "false")
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", type + " Cache Cleared", 1000, THUMB) )
    
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
        if getSize(settingFileAccess) < 100 and getSize(nsettingFileAccess) > 100:
            Restore(nsettingFileAccess, settingFileAccess)    
    else:
        log('utils: chkSettings2, Setting2 Backup') 
        if getSize(settingFileAccess) > 100:
            Backup(settingFileAccess, nsettingFileAccess)
            if REAL_SETTINGS.getSetting("AutoBackup") == "true":
                Backup(settingFileAccess, bksettingFileAccess)
    return True
    
def backupSettings2():
    log('utils: backupSettings2')
    Backup(settingFileAccess, bksettingFileAccess)

def restoreSettings2():
    log('utils: restoreSettings2')
    dirs,files = xbmcvfs.listdir(BACKUP_LOC)
    dir,file = xbmcvfs.listdir(XMLTV_LOC)
    backuplist = [s.replace('.xml','') for s in files if s.endswith('.xml')]
    if len(backuplist) == 0:
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "No Backups found", 1000, THUMB) )
        return
    select = selectDialog(backuplist, 'Select backup to restore')   
    if select != -1:
        if dlg.yesno("PseudoTV Live", 'Restoring will remove current channel configurations, Are you sure?'):                        
            Restore(((backuplist[select])+'.xml'), settingFileAccess)
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Restore Complete", 1000, THUMB) )

def purgeSettings2():
    log('utils: purgeSettings2')
    if dlg.yesno("PseudoTV Live", 'Are you sure you want to remove all previous backups?'):       
        dirs,files = xbmcvfs.listdir(BACKUP_LOC)
        for i in range(len(files)):
            try:
                FileAccess.delete(os.path.join(BACKUP_LOC,files[i]))
            except:
                pass
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Backup Purge Complete", 1000, THUMB) )

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
    
    # Check if autoplay is enabled
    chkAutoplay()
    
    # Call showChangeLog like this to workaround bug in openElec, *Thanks spoyser
    xbmc.executebuiltin("RunScript(" + ADDON_PATH + "/utilities.py,-showChangelog)")
    
def preStart(): 
    log('utils: preStart')
    # VideoWindow Patch.
    VideoWindow()
    
    if isDebug() == True:
        if yesnoDialog('Its recommended you disable debug logging for standard use','Disable Debugging?') == True:
            REAL_SETTINGS.setSetting('enable_Debug', "false")
            
    # Optimize settings based on sys.platform
    chkLowPower()
    
    # Clear filelist Caches    
    if REAL_SETTINGS.getSetting("ClearCache") == "true":
        ClearCache('Filelist')
        
    # Clear Artwork Folders
    if REAL_SETTINGS.getSetting("ClearLiveArt") == "true":
        ClearCache('Art')
            
    # Backup/Restore settings2
    if chkSettings2() == True:
        return True