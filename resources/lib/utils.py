#   Copyright (C) 2016 Kevin S. Graer
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

import os, re, sys, time, zipfile, threading, requests, random, traceback
import urllib, urllib2, cookielib, base64, fileinput, shutil, socket, httplib, urlparse, HTMLParser, zlib
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon
import time, _strptime, string, datetime, ftplib, hashlib, smtplib, feedparser, imp

from functools import wraps
from Globals import * 
from Queue import Queue
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders
from xml.dom.minidom import parse, parseString
from xml.etree import ElementTree
from urllib import unquote, quote
from urllib2 import HTTPError, URLError
from pyfscache import *
from hdhr import hdhr
from FileAccess import FileAccess

sys.setcheckinterval(25)
socket.setdefaulttimeout(15)
                    
USERAGENT   = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
httpHeaders = {'User-Agent': USERAGENT,
                        'Accept':"application/json, text/javascript, text/html,*/*",
                        'Accept-Encoding':'gzip,deflate,sdch',
                        'Accept-Language':'en-US,en;q=0.8'
                       }

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json
    
################
# Github Tools #
################
     
def isKodiRepo(plugin=''):
    log("utils: isKodiRepo")
    # parse kodi repo, collect video, music plugins
    # if necessary limit plugins to kodi approved.
    # currently not being used
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
    krypton = 'https://github.com/xbmc/repo-plugins/tree/krypton'
    
    repoItems = []
    repoItems = fillGithubItems(dharma)
    repoItems += fillGithubItems(eden)
    repoItems += fillGithubItems(frodo)
    repoItems += fillGithubItems(gotham)
    repoItems += fillGithubItems(helix)
    repoItems += fillGithubItems(isengard)
    repoItems += fillGithubItems(jarvis)
    repoItems += fillGithubItems(krypton)
    
    RepoPlugins = []
    for i in range(len(repoItems)):
        if (repoItems[i]).lower().startswith('plugin.video.'):
            RepoPlugins.append((repoItems[i]).split(' ')[0])
        elif (repoItems[i]).lower().startswith('plugin.music.'):
            RepoPlugins.append((repoItems[i]).split(' ')[0])
            
    del repoItems[:]
    if addon in RepoPlugins:
        return True
    else:
        return False

def fillGithubItems(url, ext=None, removeEXT=False):
    log("utils: fillGithubItems, url = " + url)
    Sortlist = []
    try:
        list = []
        catlink = re.compile('title="(.+?)">').findall(read_url_cached(url))
        for i in range(len(catlink)):
            link = catlink[i]
            name = (catlink[i]).lower()
            if ext != None:
                if name.endswith(ext.lower()):
                    if removeEXT == True:
                        link = os.path.splitext(os.path.basename(link))[0]
                    list.append(link.replace('&amp;','&'))
            else:
                list.append(link.replace('&amp;','&'))
        Sortlist = sorted_nicely(list) 
        log("utils: fillGithubItems, found %s items" % str(len(Sortlist)))
    except Exception,e:
        pass
    return Sortlist

##############
# LOGO Tools #
##############
        
def CleanCHname(text):
    text = text.lower()
    text = text.replace("ae", "a&e")
    text = text.replace("(uk)", "")
    text = text.replace("(us)", "")
    text = text.replace("(ca)", "")
    text = text.replace("(en)", "")
    text = text.replace("hd", "")
    text = text.replace("pvr", "")
    text = text.replace("ustv", "") 
    text = text.replace("hdhr", "")
    return text.strip(' ').rstrip(' ')
  
def CleanCHnameSeq(text):
    # try removing number from channel ie NBC2 = NBC, or 5 FOX = FOX
    return (''.join(i for i in text if not i.isdigit())).lstrip()
                
def FindLogo(chtype, chname, mediapath=None):
    log('utils: FindLogo')
    if len(chname) == 0 or REAL_SETTINGS.getSetting('Enable_FindLogo') == "false":
        return
    try:
        FindLogoThread = threading.Timer(0.5, FindLogo_Thread, [chtype, chname, mediapath])
        if FindLogoThread.isAlive():
            FindLogoThread.join()
        FindLogoThread = threading.Timer(0.5, FindLogo_Thread, [chtype, chname, mediapath])
        FindLogoThread.name = "FindLogoThread"
        FindLogoThread.start()
    except Exception,e:
        log('utils: FindLogo, failed! ' + str(e))
            
def FindLogo_Thread(chtype, chname, mediapath):
    log("utils: FindLogo_URL, chtype = " + str(chtype) + ", chname = " + chname)
    if FileAccess.exists(LOGO_LOC) == False:
        FileAccess.mkdirs(LOGO_LOC)  
    url = False
    LogoPath = os.path.join(LOGO_LOC,chname + '.png')
    LogoPath_Ani = os.path.join(LOGO_LOC,chname + '.gif')
    clean_chname = CleanCHname(chname)

    if REAL_SETTINGS.getSetting('Enable_AnimLogo') == "true":
        if FileAccess.exists(LogoPath_Ani) == False:
            if chtype in [0,1,2,3,4,5,8,9,12,13,14,15]:
                log("utils: FindLogo_URL, findGithubLogo animated")
                url = findGithubLogo(clean_chname, animated=True) 
                if url:
                    GrabLogo(url, chname, LogoPath_Ani) 

    if REAL_SETTINGS.getSetting('Enable_FindLogo') == "true":
        if FileAccess.exists(LogoPath) == False:
            # thelogodb search
            if chtype in [0,1,8,9,15]:
                log("utils: FindLogo_URL, findLogodb")
                url = findLogodb(clean_chname)
                if url:
                    GrabLogo(url, chname, LogoPath)
                    
            if not url:
                # github search
                if chtype in [0,1,2,3,4,5,8,9,12,13,14,15]:
                    log("utils: FindLogo_URL, findGithubLogo")
                    url = findGithubLogo(clean_chname)
                    if url:
                        GrabLogo(url, chname, LogoPath)
                    else:
                        url = findGithubLogo(CleanCHnameSeq(clean_chname))
                        if url:
                            GrabLogo(url, chname, LogoPath)

            # local tvshow logo search
            if mediapath and chtype == 6:
                log("utils: FindLogo_URL, local TVlogo")
                mpath = getMpath(mediapath)
                smpath = mpath.rsplit('/',2)[0] #Path Above mpath ie Series folder
                artSeries = xbmc.translatePath(os.path.join(smpath, 'logo.png'))
                artSeason = xbmc.translatePath(os.path.join(mpath, 'logo.png'))
                if FileAccess.exists(artSeries): 
                    url = artSeries
                elif FileAccess.exists(artSeason): 
                    url = artSeason
                if url:
                    GrabLogo(url, chname, LogoPath_Ani) 

def GrabLogo(url, chname, LogoFile=''):
    url = url.rstrip('/')
    if not LogoFile:
        LogoFile = os.path.join(LOGO_LOC, chname + '.png')
    log("utils: GrabLogo, url = " + url + " ,LogoFile = " + LogoFile) 
    
    if FileAccess.exists(LogoFile) == False:
        if url.startswith('image'):
            url = (unquote(url)).replace("image://",'')
            GrabLogo(url, chname, LogoFile)
        elif url.startswith('http'):
            download_silent(url, LogoFile)
        else:
            FileAccess.copy(xbmc.translatePath(url), LogoFile) 

def findLogodb(chname):
    try:
        user_region = REAL_SETTINGS.getSetting('limit_preferred_region')
        user_type = REAL_SETTINGS.getSetting('LogoDB_Type')
        useMix = REAL_SETTINGS.getSetting('LogoDB_Fallback') == "true"
        useAny = REAL_SETTINGS.getSetting('LogoDB_Anymatch') == "true"
        urlbase = 'http://www.thelogodb.com/api/json/v1/%s/tvchannel.php?s=' % LOGODB_API_KEY
        chanurl = (urlbase+chname).replace(' ','%20')
        log("utils: findLogodb, chname = " + chname + ', url = ' + chanurl)
        typelst =['strLogoSquare','strLogoSquareBW','strLogoWide','strLogoWideBW','strFanart1']
        user_type = typelst[int(user_type)]
        detail = re.compile("{(.*?)}", re.DOTALL ).findall(read_url_cached(chanurl))
        MatchLst = []
        mixRegionMatch = []
        mixTypeMatch = []
        image = False
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
                            if channel.lower() == chname:
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
        
        # cleanup
        del MatchLst[:]
        del mixRegionMatch[:]
        del mixTypeMatch[:]      
        return image 
    except Exception,e:
        log("utils: findLogodb, Failed! " + str(e))
         
def findGithubLogo(chname, animated=False): 
    log("utils: findGithubLogo, chname = " + chname + ', animated = ' + str(animated))
    url = False
    if animated == True:
        baseurl='https://github.com/PseudoTV/PseudoTV_Logos/tree/master/_Animated/'+(chname[0]).upper()
        Studiolst = fillGithubItems(baseurl, '.gif', removeEXT=True)
        if not Studiolst:
            miscurl='https://github.com/PseudoTV/PseudoTV_Logos/tree/master/_Animated/0'
            Misclst = fillGithubItems(miscurl, '.gif', removeEXT=True)
            for i in range(len(Misclst)):
                Studio = Misclst[i]
                if uni((Studio).lower()) == uni(chname.lower()):
                    url = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/_Animated/0/'+((Studio+'.gif').replace('&','&amp;').replace(' ','%20'))
                    log('utils: findGithubLogo, Logo Match: ' + Studio.lower() + ' = ' + (Misclst[i]).lower())
                    break
        else:
            for i in range(len(Studiolst)):
                Studio = Studiolst[i]
                if uni((Studio).lower()) == uni(chname.lower()):
                    url = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/_Animated/'+(chname[0]).upper()+'/'+((Studio+'.gif').replace('&','&amp;').replace(' ','%20'))
                    log('utils: findGithubLogo, Logo Match: ' + Studio.lower() + ' = ' + (Studiolst[i]).lower())
                    break
    else:
        baseurl='https://github.com/PseudoTV/PseudoTV_Logos/tree/master/'+(chname[0]).upper()
        Studiolst = fillGithubItems(baseurl, '.png', removeEXT=True)
        if not Studiolst:
            miscurl='https://github.com/PseudoTV/PseudoTV_Logos/tree/master/0'
            Misclst = fillGithubItems(miscurl, '.png', removeEXT=True)
            for i in range(len(Misclst)):
                Studio = Misclst[i]
                if uni((Studio).lower()) == uni(chname.lower()):
                    url = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/0/'+((Studio+'.png').replace('&','&amp;').replace(' ','%20'))
                    log('utils: findGithubLogo, Logo Match: ' + Studio.lower() + ' = ' + (Misclst[i]).lower())
                    break
        else:
            for i in range(len(Studiolst)):
                Studio = Studiolst[i]
                if uni((Studio).lower()) == uni(chname.lower()):
                    url = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Logos/master/'+(chname[0]).upper()+'/'+((Studio+'.png').replace('&','&amp;').replace(' ','%20'))
                    log('utils: findGithubLogo, Logo Match: ' + Studio.lower() + ' = ' + (Studiolst[i]).lower())
                    break
    return url
    
def hasAPI(key):
    if isPlugin(key) == True:
        set_Kodi_JSON(decodeString(DOX_API_KEY) %key)
        
#######################
# Communication Tools #
#######################

def GA_Request():
    log("GA_Request")   
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
        
        if getProperty("Verified_Community") == "true":
            OPTIONS = OPTIONS + ['COM:True']
                    
        if isContextInstalled():
            OPTIONS = OPTIONS + ['CM:True']
            
        if isCompanionInstalled():
            OPTIONS = OPTIONS + ['CP:True']
            
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
        # if REAL_SETTINGS.getSetting('ga_disable') == 'false':
        urllib2.urlopen(URL).info()
        # else:
            # sendShout(str(OPTIONS))
    except Exception,e:  
        log("GA_Request Failed" + str(e), xbmc.LOGERROR)

def RSS_API():
    log('utils: RSS_API')
    try:
        list = (open_url('http://raw.githubusercontent.com/Lunatixz/XBMC_Addons/master/rss_api.xml')).read()
    except:
        list = ''
    return list

def LOW_MSG():
    log('utils: LOW_MSG')
    try:
        list = (open_url('http://raw.githubusercontent.com/Lunatixz/XBMC_Addons/master/low_msg.xml')).read()
    except:
        list = ''
    return list
    
def POP_MSG():
    log('utils: POP_MSG')
    try:
        list = (open_url('http://raw.githubusercontent.com/Lunatixz/XBMC_Addons/master/pop_msg.xml')).read().replace('\n','').replace('\r','').replace('\t','')
    except:
        list = ''
    return list

def UpdateRSS():
    log('utils: UpdateRSS')
    try:
        UpdateRSSthread = threading.Timer(0.5, UpdateRSS_Thread)
        if UpdateRSSthread.isAlive():
            UpdateRSSthread.cancel() 
        UpdateRSSthread = threading.Timer(0.5, UpdateRSS_Thread)
        UpdateRSSthread.name = "UpdateRSSthread"
        UpdateRSSthread.start()
    except Exception,e:
        log('utils: UpdateRSS, failed! ' + str(e))
         
def UpdateRSS_Thread():
    log('utils: UpdateRSS_Thread')
    try:
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
                twitrss = 'http://twitrss.me/twitter_user_to_rss/?user=PseudoTV_Live'
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
            setProperty("twitter.1.label", uni(pushlist))
            setProperty("twitter.2.label", uni(gitlist))
            setProperty("twitter.3.label", uni(twitlist)) 
    except:
        pass
        
# Adapted from KodeKarnage's lazytv
def sendShout(txt):
    log('utils: sendShout')
    thyme = time.time()
    recipient = 'pseudotvsubmit@gmail.com'
    
    body = '<table border="1">'
    body += '<tr><td>%s</td></tr>' % txt
    body += '</table>'
    
    msg = MIMEText(body, 'html')
    msg['Subject'] = 'PseudoTV Live +1  %s' % thyme
    msg['From'] = 'PseudoTV Live'
    msg['To'] = recipient
    msg['X-Mailer'] = 'PseudoTV Live Shout Out %s' % thyme

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
     
def download_silent_thread(url, dest):
    log('download_silent_thread')
    try:
        urllib.urlretrieve(url, dest)
    except Exception,e:
        log('utils: download_silent_thread, Failed!,' + str(e))

def download_silent(url, dest):
    log('download_silent')
    try:
        download_silentThread = threading.Timer(0.5, download_silent_thread, [url, dest])
        if download_silentThread.isAlive():
            download_silentThread.join()
        download_silentThread = threading.Timer(0.5, download_silent_thread, [url, dest])
        download_silentThread.name = "download_silentThread"
        download_silentThread.start()
    except Exception,e:
        log('utils: download_silent, failed! ' + str(e))

@cache_hourly
def getRequest(url, udata=None, headers=httpHeaders, dopost = False):
    log("utils: getRequest")
    req = urllib2.Request(url.encode('utf-8'), udata, headers)
    if dopost == True:
        method = "POST"
        req.get_method = lambda: method
    try:
        response = urllib2.urlopen(req)
        page = response.read()
        if response.info().getheader('Content-Encoding') == 'gzip':
            log("Content Encoding == gzip")
            page = zlib.decompress(page, zlib.MAX_WBITS + 16)
    except Exception,e:
        log('utils: getRequest, Failed!,' + str(e))
        page = ""
    return page
    
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
        pass
        
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
        pass
  
def open_url(url, userpass=None):
    log("utils: open_url")
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
        return ''
         
def retrieve_url(url, userpass, dest):
    log("utils: retrieve_url")
    try:
        resource = open_url(url, userpass)
        output = open(dest, 'w')
        output.write(resource.read())  
        output.close()
        return True
    except Exception, e:
        return False 
       
def get_data(url, data_type ='json'):
    log('utils: get_data, url = ' + url)
    data = []
    try:
        request = read_url_cached_monthly(url)
        if data_type == 'json':
            data = json.loads(request)
            if not data:
                data = 'Empty'
        else:
            data = request
    except Exception, e:
        data = 'Empty'
    return data
        
##################
# Zip Tools #
##################

def all(_in, _out, dp=None):
    if dp:
        dp = xbmcgui.DialogProgress()
        dp.create("PseudoTV Live","Extracting Files", ' ', ' ')
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

def handle_wait(time_to_wait,string=None,header=ADDON_NAME): #*Thanks enen92
    dlg = xbmcgui.DialogProgress()
    dlg.create(header)
    secs=0
    percent=0
    increment = int(100 / time_to_wait)
    cancelled = False
    while secs < time_to_wait:
        secs += 1
        percent = increment*secs
        secs_left = str((time_to_wait - secs))
        if not string:
            string = "Starts In %s seconds, Cancel Channel Change?"
        remaining_display = string.replace('%s',str(secs_left))
        dlg.update(percent,remaining_display)
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
    
def Unavailable():
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Unavailable", 1000, THUMB) )
    
def TryAgain():
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Try Again Later...", 1000, THUMB) )

def is_busy_dialog():
    return xbmc.getCondVisibility('Window.IsActive(busydialog)')
    
def show_busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialog)')

def hide_busy_dialog():
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    while is_busy_dialog():
        xbmc.sleep(100)
        
def Error(line1= '', line2= '', line3= '',header=ADDON_NAME):
    setProperty('PTVL.ERROR_LOG', ' '.join([line1,line2,line3]))
    okDialog( line1, line2, line3, header)
    
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
        
def currentWindow():
    currentWindow = ''
    # return current window label via json, xbmcgui.getCurrentWindowId does not return accurate id.
    json_query = ('{"jsonrpc": "2.0", "method":"GUI.GetProperties","params":{"properties":["currentwindow"]}, "id": 1}')
    json_detail = sendJSON(json_query)
    file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
    for f in file_detail:
        id = re.search('"label" *: *"(.*?)"', f)
        if id and len(id.group(1)) > 0:
            currentWindow = id.group(1)
            break
    log("utils: currentWindow = " + currentWindow)
    return currentWindow
         
# General
def infoDialog(message, header=ADDON_NAME, show=True, sound=False, time=1000, icon=THUMB):
    setProperty('PTVL.NOTIFY_LOG', message)
    log('utils: infoDialog: ' + message)
    if show == True:
        try: 
            xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except Exception,e:
            log("utils: infoDialog Failed! " + str(e))
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, THUMB))

# Error
def ErrorNotify(message, header=ADDON_NAME, show=True, sound=True, time=1000, icon=THUMB):
    infoDialog("ERROR: " + message, header, show, sound, time, icon)

# Debug
def DebugNotify(message, header=ADDON_NAME, show=DEBUG, sound=False, time=1000, icon=THUMB):
    infoDialog("DEBUGGING: " + message, header, show, sound, time, icon)

# Optional
def OptNotify(message, header=ADDON_NAME, show=NOTIFY, sound=False, time=1000, icon=THUMB):
    infoDialog(message, header, show, sound, time, icon)
    
def okDialog(str1, str2='', str3='', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, str1, str2, str3)
    
def textViewer(text, header=ADDON_NAME):
    xbmcgui.Dialog().textviewer(header, text)
    
def browse(type=0, heading=ADDON_NAME, shares='', mask='', useThumbs=True, treatAsFolder=False, default='', enableMultiple=False):
    return xbmcgui.Dialog().browse(type, heading, shares, mask, useThumbs, treatAsFolder, default, enableMultiple)
    # Types:
    # - 0 : ShowAndGetDirectory
    # - 1 : ShowAndGetFile
    # - 2 : ShowAndGetImage
    # - 3 : ShowAndGetWriteableDirectory

def browseMultiple(type=0, shares='', mask='', useThumbs=True, treatAsFolder=True, default='', heading=ADDON_NAME):
    return xbmcgui.Dialog().browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)

def browseSingle(type=0, shares='', mask='', useThumbs=True, treatAsFolder=True, default='', heading=ADDON_NAME):
    return xbmcgui.Dialog().browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)

def selectDialog(list, header=ADDON_NAME, autoclose=0, preselect=0):
    if len(list) > 0:#todo preselect
        select = xbmcgui.Dialog().select(header, list, autoclose)
        return select

def mselectDialog(list, header=ADDON_NAME, autoclose=0, preselect=0):
    if len(list) > 0:#todo preselect
        select = xbmcgui.Dialog().multiselect(header, list, autoclose)
        return select

def matchSelect(list, name):
    if name:
        for i in range(len(list)):
            if name.lower() == list[i].lower():
                return i
        
def matchMselect(list, select):
    if select:
        slist = []
        for i in range(len(select)):
            slist.append(list[select[i]]) 
        return slist

def inputDialog(heading, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
    # Types:
    # - xbmcgui.INPUT_ALPHANUM (standard keyboard)
    # - xbmcgui.INPUT_NUMERIC (format: #)
    # - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
    # - xbmcgui.INPUT_TIME (format: HH:MM)
    # - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
    # - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
    retval = xbmcgui.Dialog().input(heading, default, key, opt, close)
    return retval    
    
def yesnoDialog(str1, str2='', header=ADDON_NAME, yes='', no=''):
    answer = xbmcgui.Dialog().yesno(header, str1, str2, '', yes, no)
    return answer
     
##################
# Property Tools #
##################

def getProperty(str):
    try:
        return xbmcgui.Window(10000).getProperty(str)
    except Exception,e:
        log("utils: getProperty, Failed! " + str(e))
        return ''
          
def setProperty(str1, str2):
    try:
        ALL_PROPERTIES.append(str1)
        xbmcgui.Window(10000).setProperty(str1, str2)
    except Exception,e:
        log("utils: setProperty, Failed! " + str(e))
        
def clearProperty(str):
    xbmcgui.Window(10000).clearProperty(str)
     
##############
# XBMC Tools #
##############
 
def appendPlugin(list):
    nlist = []
    for i in range(len(list)):
        nlist.append('plugin://'+list[i])
    return nlist
 
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

def sendJSON(command):
    data = ''
    try:
        data = xbmc.executeJSONRPC(uni(command))
    except UnicodeEncodeError:
        data = xbmc.executeJSONRPC(ascii(command))
    return uni(data)
     
def set_Kodi_JSON(params):
    xbmc.executeJSONRPC('{"jsonrpc": "2.0", %s, "id": 1}' % params)
    
def get_Kodi_JSON(params):
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", %s, "id": 1}' % params)
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    return json.loads(json_query)
    
def isPlugin(plugin):
    status = False
    if plugin[0:9] == 'plugin://':
        plugin = plugin.replace("plugin://","")
        addon = splitall(plugin)[0]
    else:
        addon = plugin
        
    if addon not in chkPSS(PSS_API_KEY):
        status = xbmc.getCondVisibility('System.HasAddon(%s)' % addon) == 1
    return status

def videoIsPlaying():
    return xbmc.getCondVisibility('Player.HasVideo')

def getXBMCVersion():
    log("utils: getXBMCVersion")
    return int((xbmc.getInfoLabel('System.BuildVersion').split('.'))[0])
 
def getPlatform():
    platform = chkPlatform()
    setProperty("PTVL.Platform",platform)
    log("utils: getPlatform = " + platform)
    return platform
    
def chkPlatform():
    log("utils: chkPlatform")
    chkLanguage()
    if xbmc.getCondVisibility('System.Platform.Linux'):
        REAL_SETTINGS.setSetting('environment', "3")
    elif xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi'):
        REAL_SETTINGS.setSetting('environment', "5")
        REAL_SETTINGS.setSetting('platform', "4")
        return "rPi"
    elif xbmc.getCondVisibility('System.Platform.Windows'):
        REAL_SETTINGS.setSetting('environment', "6")
    elif xbmc.getCondVisibility('System.Platform.OSX'):
        REAL_SETTINGS.setSetting('environment', "4")
        REAL_SETTINGS.setSetting('platform', "3")   
        return "MAC"
    elif xbmc.getCondVisibility('System.Platform.IOS'):
        REAL_SETTINGS.setSetting('environment', "2")
        REAL_SETTINGS.setSetting('platform', "2")
        return "iOS"
    elif xbmc.getCondVisibility('System.Platform.Darwin'):
        REAL_SETTINGS.setSetting('environment', "3")
    elif xbmc.getCondVisibility('System.Platform.ATV2'):
        REAL_SETTINGS.setSetting('environment', "1")
        REAL_SETTINGS.setSetting('platform', "1")
        return "ATV"
    elif xbmc.getCondVisibility('System.Platform.Android'):
        REAL_SETTINGS.setSetting('environment', "0")
        REAL_SETTINGS.setSetting('platform', "0")
        return "Android"
    elif REAL_SETTINGS.getSetting("platform") in ["5","7"]: 
        return "APU"
    elif REAL_SETTINGS.getSetting("platform") in ["6","8"]: 
        return "Pro"
    return "Unknown"

def chkLanguage():
    langs = ["Chinese","Dutch","English","Finnish","French","German","Hungarian","Italian","Japanese","Polish","Portuguese","Russian","Spanish","Swedish"]
    for l in range(len(langs)):
        if langs[l].lower() in (xbmc.getInfoLabel('System.Language')).lower():
            REAL_SETTINGS.setSetting('preferred_language', langs[l])
            
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
        
def hash2string(string):
    return hashlib.md5(string).hexdigest()

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
        try:
            f = FileAccess.open(file)
            size = f.size()
            f.close()
        except:
            size = 0
        log('utils: getSize = ' + str(size))
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
        FileAccess.mkdirs(os.path.join(thepath))
    
    thefile = os.path.join(thepath,thefile)
    try:
        fle = open(thefile, "w")
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
            fle = open(thefile, "r")
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
            fle = open(thefile, "r")
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
        FileAccess.mkdirs(STRM_CACHE_LOC)
    path = (mediapath.encode('base64'))[:16] + '.strm'
    filepath = os.path.join(STRM_CACHE_LOC,path)
    if FileAccess.exists(filepath):
        return filepath
    else:
        fle = open(filepath, "w")
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
        OptNotify("Backup Complete")
       
def Restore(bak, org):
    log('utils: Restore ' + str(bak) + ' - ' + str(org))
    if FileAccess.exists(bak):
        if FileAccess.exists(org):
            try:
                FileAccess.delete(org)
            except:
                pass
        FileAccess.rename(bak, org)
        infoDialog("Restore Complete, Restarting...")
 
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
    infoDialog(MSG)
      
def getContext():  
    log('utils: getContext')
    url='https://github.com/Lunatixz/XBMC_Addons/raw/master/zips/context.pseudotv.live.export/context.pseudotv.live.export-1.0.8.zip'
    name = 'context.pseudotv.live.export.zip' 
    MSG = 'PseudoTV Live Context Export'    
    path = xbmc.translatePath(os.path.join('special://home/addons','packages'))
    addonpath = xbmc.translatePath(os.path.join('special://','home/addons'))
    lib = os.path.join(path,name)
    getGithubZip(url, lib, addonpath, MSG)
 
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
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", MSG, 1000, THUMB) )
    return   
 
def chkVersion():
    log('utils: chkVersion')
    try:
        curver = xbmc.translatePath(os.path.join(ADDON_PATH,'addon.xml'))    
        source = open(curver, mode='r')
        link = source.read()
        source.close()
        match = re.compile('" version="(.+?)" name="PseudoTV Live"').findall(link)
        
        for vernum in match:
            log("utils: chkVersion, Current Version = " + str(vernum))

        link = open_url(decodeString('aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL0x1bmF0aXh6L1hCTUNfQWRkb25zL21hc3Rlci9zY3JpcHQucHNldWRvdHYubGl2ZS9hZGRvbi54bWw=')).read() 
        link = link.replace('\r','').replace('\n','').replace('\t','').replace('&nbsp;','')
        match = re.compile('" version="(.+?)" name="PseudoTV Live"').findall(link)

        if len(match) > 0:
            log("utils: chkVersion, Repo Version = " + str(match[0]))
            if vernum != str(match[0]):
                if isRepoInstalled() == False:
                    getRepo()
                    # okDialog('Your current build of PseudoTV Live v.%s is outdated,' %str(vernum), 'The latest build is v.%s' %str(match[0]),'Please remember to update regularly, Thank You')
                else:
                    set_Kodi_JSON(decodeString('Im1ldGhvZCI6IkFkZG9ucy5TZXRBZGRvbkVuYWJsZWQiLCJwYXJhbXMiOnsiYWRkb25pZCI6InJlcG9zaXRvcnkubHVuYXRpeHoiLCJlbmFibGVkIjp0cnVlfQ=='))
                xbmc.executebuiltin('UpdateAddonRepos')
                xbmc.executebuiltin('UpdateLocalAddons')
        return isRepoInstalled()
    except:
        return True
    
def isCompanionInstalled():
    companion = isPlugin('plugin.video.pseudo.companion')
    log('utils: isCompanionInstalled = ' + str(companion))
    return companion
    
def isContextInstalled():
    context = isPlugin('context.pseudotv.live.export')
    log('utils: isContextInstalled = ' + str(context))
    return context
    
def isRepoInstalled():
    repo = isPlugin('repository.lunatixz')
    log('utils: isRepoInstalled = ' + str(repo))
    return repo

def chkKodiSkin():
    if xbmc.getSkinDir() in ('skin.confluence', 'skin.estuary'):
        okDialog("Its recommended you don't use Kodi's"+' "Default skin", Please select another Kodi Skin for the best viewing experience.')
    
def chkAutoplay(silent=False):
    log('utils: chkAutoplay')
    fle = xbmc.translatePath("special://profile/guisettings.xml")
    try:
        xml = open(fle, "r")
        dom = parse(xml)
        autoplaynextitem = dom.getElementsByTagName('autoplaynextitem')
        Videoautoplaynextitem  = (autoplaynextitem[0].childNodes[0].nodeValue.lower() == 'true')
        Musicautoplaynextitem  = (autoplaynextitem[1].childNodes[0].nodeValue.lower() == 'true')
        xml.close()
        log('utils: chkAutoplay, Videoautoplaynextitem is ' + str(Videoautoplaynextitem)) 
        log('utils: chkAutoplay, Musicautoplaynextitem is ' + str(Musicautoplaynextitem)) 
        totcnt = Videoautoplaynextitem + Musicautoplaynextitem
        if totcnt > 0:
            setProperty("PTVL.Autoplay","true")
            if not silent:
                okDialog("Its recommended you disable Kodi's"+' "Play the next video/song automatically" ' + "feature found under Kodi's video/playback and music/playback settings.")
        else:
            raise Exception()
    except:
        setProperty("PTVL.Autoplay","false") 
        pass
       
def chkLowPower(): 
    chkHeadless()
    setProperty("PTVL.LOWPOWER","false") 
    if REAL_SETTINGS.getSetting("Override.LOWPOWER") == "false":
        if getPlatform() in ['rPi','iOS','ATV','Android']:
            setProperty("PTVL.LOWPOWER","true")
            REAL_SETTINGS.setSetting('MEDIA_LIMIT', "0")
            REAL_SETTINGS.setSetting('SFX_Enabled', "false")
            REAL_SETTINGS.setSetting('EPG.xInfo', "false")
            REAL_SETTINGS.setSetting('Disable_Watched', "false")
            REAL_SETTINGS.setSetting('Idle_Screensaver', "false")
            REAL_SETTINGS.setSetting('IncludeMeta', "false")
            REAL_SETTINGS.setSetting('respectChannels', "false")
            REAL_SETTINGS.setSetting('Cache_Enabled', "false")
            
            if int(REAL_SETTINGS.getSetting('Enable_ChannelBug')) > 1:
                REAL_SETTINGS.setSetting('Enable_ChannelBug', "1")
            
            REAL_SETTINGS.setSetting('EnableSettop', "false")
            if int(REAL_SETTINGS.getSetting('ChannelResetSetting')) in [0,5]:
                REAL_SETTINGS.setSetting('ChannelResetSetting', "2")
                
            infoDialog("Settings Optimized for Performance")
    else:
        log("utils: chkLowPower Override = True")
    log("utils: LOWPOWER = " + getProperty("PTVL.LOWPOWER"))
    
def chkHeadless():     
    setProperty("PTVL.SHARING","false") 
    setProperty("PTVL.HEADLESS","false") 
    if CHANNEL_SHARING == True:
        setProperty("PTVL.SHARING","true") 
        REAL_SETTINGS.setSetting('IncludeBCTs', "false")
        if HEADLESS_SHARING == True:
            setProperty("PTVL.HEADLESS","true") 
            REAL_SETTINGS.setSetting('AutoStart', "2")
            REAL_SETTINGS.setSetting('AutoOff', "0")
            REAL_SETTINGS.setSetting('Idle_Screensaver', "false")
            REAL_SETTINGS.setSetting('EnableNotify', "false")
            REAL_SETTINGS.setSetting('SFX_Enabled', "false")
            REAL_SETTINGS.setSetting('DisablePlayback', "true")
            REAL_SETTINGS.setSetting('EPG.xInfo', "false")
            REAL_SETTINGS.setSetting('Enable_ChannelBug', "0")
    log("utils: SHARING = " + getProperty("PTVL.SHARING"))
    log("utils: HEADLESS = " + getProperty("PTVL.HEADLESS"))

def isLowPower():
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
    for i in range(CHANNEL_LIMIT):
        try:
            FileAccess.delete(CHANNELS_LOC + 'channel_' + str(i) + '.m3u')
        except:
            pass
    infoDialog("Channel Playlists Cleared")
          
def ClearCache(type='Files'):
    log('utils: ClearCache ' + type)  
    if type == 'Cache':
        try:
            daily.delete("%") 
            weekly.delete("%")
            monthly.delete("%")
        except:
            pass
        REAL_SETTINGS.setSetting('ClearCache', "false")
    elif type == 'Files':
        try:
            shutil.rmtree(GEN_CHAN_LOC)
        except:
            pass
        try:
            shutil.rmtree(MADE_CHAN_LOC)
        except:
            pass
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
            FileAccess.mkdirs(BACKUP_LOC)
        except Exception,e:
            pass
            
    if Normal_Shutdown == False:
        log('utils: chkSettings2, Setting2 Restore') 
        if getSize(SETTINGS_FLE) < SETTINGS_FLE_DEFAULT_SIZE and getSize(SETTINGS_FLE_LASTRUN) > SETTINGS_FLE_DEFAULT_SIZE:
            Restore(SETTINGS_FLE_LASTRUN, SETTINGS_FLE)
    else:
        log('utils: chkSettings2, Setting2 Backup')
        if REAL_SETTINGS.getSetting("AutoBackup") == "true":               
            backupSettings2()
    return
    
def cleanBackupSettings2():
    dirs,files = FileAccess.listdir(BACKUP_LOC)
    for file in files:
        try:
            max = datetime.datetime.now() + datetime.timedelta(days=7)
            try:
                epoch = datetime.datetime.strptime((re.compile('settings2.(.+?).xml').findall(file)[0]),"%Y-%m-%d.%H.%M.%S")
            except:
                epoch = datetime.datetime.strptime((re.compile('settings2.(.+?).xml').findall(file)[0]),"%Y-%m-%d.%H.%M.%S")
            if max > epoch:
                log('utils: cleanBackupSettings2, cleaning ' + ascii(file))
                FileAccess.delete(os.path.join(BACKUP_LOC,file))
        except Exception,e:
            pass

def backupSettings2():
    log('utils: backupSettings2')
    cleanBackupSettings2()
    SETTINGS_FLE_BACKUP = os.path.join(BACKUP_LOC, 'settings2.' + (datetime.datetime.now().strftime("%Y-%m-%d.%H.%M.%S")) + '.xml')
    Backup(SETTINGS_FLE, SETTINGS_FLE_BACKUP)
    if FileAccess.exists(SETTINGS_FLE_BACKUP) == False:
        ErrorNotify("Backup Failed")

def restoreSettings2():
    log('utils: restoreSettings2')
    dirs,files = FileAccess.listdir(BACKUP_LOC)
    dir,file = FileAccess.listdir(XMLTV_LOC)
    backuplist = [s.replace('.xml','') for s in files if s.endswith('.xml')]
    if backuplist and len(backuplist) > 0:
        backuplist.reverse()
        select = selectDialog(backuplist, 'Select backup to restore')   
        if select != -1:
            RESTORE_FILE = backuplist[select]+'.xml'
            RESTORE_FLEPATH = os.path.join(BACKUP_LOC, RESTORE_FILE)
            if yesnoDialog('Restoring will remove current channel configurations, Are you sure?'):
                Restore(RESTORE_FLEPATH, SETTINGS_FLE)
                if getSize(SETTINGS_FLE) == getSize(RESTORE_FLEPATH):
                    REAL_SETTINGS.setSetting('ForceChannelReset', 'true')
                    return infoDialog("Restore Complete")
    else:
        return infoDialog("No Backups found")
         
def chkPSS(list):
    try:
        nlist = []
        list = list.split('|')
        for i in range(len(list)):
            nlist.append(decodeString(list[i]))
        return nlist 
    except:
        pass
                  
def purgeSettings2():
    log('utils: purgeSettings2')
    if yesnoDialog('Are you sure you want to remove all previous backups?'):       
        dirs,files = FileAccess.listdir(BACKUP_LOC)
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
    chkLowPower()
    if HEADLESS_SHARING == False:
        # Install PTVL Isengard Context Export, Workaround for addon.xml 'optional' flag not working.
        # set 'optional' as true so users can disable if unwanted.
        if getXBMCVersion() > 14 and isContextInstalled() == False:
            if yesnoDialog('Would you like to install the PseudoTV Live context export tool?'):       
                getContext()
            
        if isLowPower() == True:
            textViewer(LOW_MSG(),header="PseudoTV Live - Notification")

        # Call showChangeLog like this to workaround bug in openElec, *Thanks spoyser
        xbmc.executebuiltin("RunScript(" + ADDON_PATH + "/utilities.py,-showChangelog)")
        
        # Force Channel rebuild
        # REAL_SETTINGS.setSetting('ForceChannelReset', 'true')
        # okDialog("Forced Channel Reset Required","Please Be Patient while rebuilding channels...",header="PseudoTV Live - Notification") 
            
        chkAutoplay()
        chkKodiSkin()
        okDialog(POP_MSG(),header="PseudoTV Live - Notification")
        
def isPTVLOutdated():
    log('utils: isPTVLOutdated')
    f = open(xbmc.translatePath(os.path.join(ADDON_PATH,'addon.xml'))  , mode='r')
    link = f.read()
    f.close()
    match = re.compile('" version="(.+?)" name="PseudoTV Live"').findall(link)
    
    for vernum in match:
        log("utils: isPTVLOutdated, Current Version = " + str(vernum))
    try:
        link = open_url('https://raw.githubusercontent.com/Lunatixz/XBMC_Addons/master/script.pseudotv.live/addon.xml').read() 
        link = link.replace('\r','').replace('\n','').replace('\t','').replace('&nbsp;','')
        match = re.compile('" version="(.+?)" name="PseudoTV Live"').findall(link)
    except:
        pass   
    if len(match) > 0:
        if vernum != str(match[0]):
            return True
    return False

def chkChanges():
    log('utils: chkChanges')
    # Media Limit Change
    CURR_MEDIA_LIMIT = REAL_SETTINGS.getSetting('MEDIA_LIMIT')
    try:
        LAST_MEDIA_LIMIT = REAL_SETTINGS.getSetting('Last_MEDIA_LIMIT')
    except:
        LAST_MEDIA_LIMIT = CURR_MEDIA_LIMIT
        REAL_SETTINGS.setSetting('Last_MEDIA_LIMIT', CURR_MEDIA_LIMIT)
    
    if CURR_MEDIA_LIMIT != LAST_MEDIA_LIMIT:
        REAL_SETTINGS.setSetting('Last_MEDIA_LIMIT', CURR_MEDIA_LIMIT)
        if CURR_MEDIA_LIMIT > LAST_MEDIA_LIMIT:
            REAL_SETTINGS.setSetting('ForceChannelReset', "true")
    
    # Bumper Type Change
    CURR_BUMPER = REAL_SETTINGS.getSetting('bumpers')
    try:
        LAST_BUMPER = REAL_SETTINGS.getSetting('Last_bumpers')
    except:
        REAL_SETTINGS.setSetting('Last_bumpers', CURR_BUMPER)
        LAST_BUMPER = REAL_SETTINGS.getSetting('Last_bumpers')
    
    if CURR_BUMPER != LAST_BUMPER:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_bumpers', CURR_BUMPER)
        
    # Commercials Type Change
    CURR_COMMERCIALS = REAL_SETTINGS.getSetting('commercials')
    try:
        LAST_COMMERCIALS = REAL_SETTINGS.getSetting('Last_commercials')
    except:
        REAL_SETTINGS.setSetting('Last_commercials', CURR_COMMERCIALS)
        LAST_COMMERCIALS = REAL_SETTINGS.getSetting('Last_commercials')
    
    if CURR_COMMERCIALS != LAST_COMMERCIALS:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_commercials', CURR_COMMERCIALS)
                
    # Trailer Type Change
    CURR_TRAILERS = REAL_SETTINGS.getSetting('trailers')
    try:
        LAST_TRAILERS = REAL_SETTINGS.getSetting('Last_trailers')
    except:
        REAL_SETTINGS.setSetting('Last_trailers', CURR_TRAILERS)
        LAST_TRAILERS = REAL_SETTINGS.getSetting('Last_trailers')
    
    if CURR_TRAILERS != LAST_TRAILERS:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_trailers', CURR_TRAILERS)

def preStart(): 
    log('utils: preStart')
    if chkVersion() == False:
        return False
        
    chkLowPower()
    chkAPIS(RSS_API())
    if HEADLESS_SHARING == False:
        # chkChanges()
        patchSeekbar()
        patchFont()

        # Disable long term debugging
        if isDebug() == True:
            if yesnoDialog('Its recommended you disable debug logging for standard use',header='PseudoTV Live - Disable Debugging?') == True:
                REAL_SETTINGS.setSetting('enable_Debug', "false")
        
    # Chk forcereset, clearcache & playlists
    if REAL_SETTINGS.getSetting("ForceChannelReset") == "true":
        ClearCache()
        ClearPlaylists()
    
    # Clear filelist Caches    
    if REAL_SETTINGS.getSetting("ClearCache") == "true":
        ClearCache('Cache')
        
    # Clear Artwork Folders
    if REAL_SETTINGS.getSetting("ClearLiveArt") == "true":
        ClearCache('Art')
            
    # Backup/Restore settings2
    chkSettings2()
    
    return True
        
##############
# PTVL Tools #
##############
    
def TimeRemainder(val):
    log("utils: TimeRemainder, val = " + str(val))
    try:
        dt = datetime.datetime.now()
        # how many secs have passed this hour
        nsecs = dt.minute*60 + dt.second + dt.microsecond*1e-6
        # number of seconds to next val hour mark
        delta = (nsecs//val)*val + val - nsecs
        log("utils: TimeRemainder, delta = " + str(delta))
    except:
        delta = 1
    return delta

def PlaylistLimit(): 
    platform = getPlatform()
    if platform in ['rPi','iOS','ATV','Android']:
        Playlist_Limit = FILELIST_LIMIT[0]
    elif platform in ['APU','MAC','Unknown']:
        Playlist_Limit = FILELIST_LIMIT[1]
    else:
        Playlist_Limit = FILELIST_LIMIT[2]
    # else:
        # Playlist_Limit = FILELIST_LIMIT[3]
    log('utils: PlaylistLimit = ' + str(Playlist_Limit))
    return Playlist_Limit

def isCom():
    return getProperty("Verified_Community") == "true"
        
def getTitleYear(showtitle, showyear=0):  
    # extract year from showtitle, merge then return
    try:
        showyear = int(showyear)
    except:
        showyear = showyear
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
   
def SEinfo(SEtitle, showSE=True):
    if SEtitle:
        try:
            SEinfo = SEtitle.split(' -')[0]
            season = int(SEinfo.split('x')[0])
            episode = int(SEinfo.split('x')[1])
        except:
            season = 0
            episode = 0   
        try:
            if showSE and season != 0 and episode != 0:
                eptitles = SEtitle.split('- ')
                eptitle = (eptitles[1] + (' - ' + eptitles[2] if len(eptitles) > 2 else ''))
                swtitle = ('S' + ('0' if season < 10 else '') + str(season) + 'E' + ('0' if episode < 10 else '') + str(episode) + ' - ' + (eptitle)).replace('  ',' ')
            else:
                swtitle = SEtitle   
        except:
            swtitle = SEtitle
        return season, episode, swtitle
    else:
        return 0, 0, ''
    
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

def help(chtype):
    log('utils: help, ' + chtype)
    HelpBaseURL = 'https://raw.githubusercontent.com/Lunatixz/XBMC_Addons/master/script.pseudotv.live/resources/help/help_'
    type = (chtype).replace('None','General')
    URL = HelpBaseURL + (type.lower()).replace(' ','%20')
    log("utils: help URL = " + URL)
    title = type + ' Configuration Help'
    f = open_url(URL)
    text = f.read()
    textViewer(text, title)

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
    log("utils: correctYoutubeSetting2")
    setting2 = setting2.replace('Multi Playlist','7').replace('Multi Channel','8').replace('Raw gdata','9')
    setting2 = setting2.replace('User Favorites','4').replace('Search Query','5').replace('User Subscription','3')
    setting2 = setting2.replace('Seasonal','31').replace('Channel','1').replace('Playlist','2')
    return setting2
     
def purgeGarbage(): 
    try:
        import gc
        # only purge when not building channel lists.
        if isBackgroundLoading() == False:
            if gc.isenabled() == False:
                log("utils: purgeGarbage, Garbage collection thresholds: %s" % (str(gc.get_threshold())))
                gc.enable()
            log("utils: purgeGarbage, Garbage collector: collected %d objects." % (gc.collect()))
            log("utils: purgeGarbage, Garbage collector: %d objects left." % (gc.collect()))
            log("utils: purgeGarbage, Garbage collector: Finished")
        elif gc.isenabled() == True:
            gc.disable()
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
    
def splitStringItem(string, opt='@#@'):
    log("utils: splitStringItem")
    return string.split(opt)
    
def joinListItem(list, opt='@#@'):
    log("utils: joinListItem")
    try:
        return opt.join(list)
    except:
        return str(list)
        
def isBackgroundVisible():
    return getProperty("OVERLAY.BackgroundVisible") == 'True'
      
def setBackgroundLabel(string=None, string2=None, string3=None):
    if string:
        setProperty("PTVL.STATUS_LOG",string) 
        setProperty("OVERLAY.BACKGROUND_TEXT",string) 
    if string2:
        setProperty("OVERLAY.BACKGROUND_TEXT2",string2) 
    if string3:
        setProperty("OVERLAY.BACKGROUND_STATUS",string3)
        
def setBackgroundProgress(val):
    setProperty("OVERLAY.BACKGROUND_PROG",str(val)) 
           
def isSFAV():
    return isPlugin('plugin.program.super.favourites')
    
def isPlayOn():
    return isPlugin('plugin.video.playonbrowser')
    
def isHDHR():
    devices = hdhr.discover()
    if devices and len(devices) > 0:
        return devices
    return False

def isPVR():
    return xbmc.getCondVisibility('Pvr.HasTVChannels')
    
def isUSTVnow():
    if isPlugin('plugin.video.ustvnow.tva'):
        return 'plugin.video.ustvnow.tva'
    elif isPlugin('plugin.video.ustvnow.plus'):
        return 'plugin.video.ustvnow.plus'
    elif isPlugin('plugin.video.ustvnow'):
        return 'plugin.video.ustvnow'
    else:
        return False

def listXMLTV():
    log("utils: listXMLTV")
    xmltvLst = []   
    EXxmltvLst = ['Enter URL']
    if isUSTVnow() != False:
        EXxmltvLst.append('ustvnow')
    if isHDHR() != False:
        EXxmltvLst.append('hdhomerun')
    if isPVR() != False:
        EXxmltvLst.append('pvr')
    dirs,files = FileAccess.listdir(XMLTV_CACHE_LOC)
    dir,file = FileAccess.listdir(XMLTV_LOC)
    xmltvcacheLst = [s.replace('.xml','') for s in files if s.endswith('.xml')] + EXxmltvLst
    xmltvLst = sorted_nicely([s.replace('.xml','') for s in file if s.endswith('.xml')] + xmltvcacheLst)
    select = selectDialog(xmltvLst, 'Select Guidedata Type', 30000)

    if select != -1:
        if xmltvLst[select] == 'Enter URL':
            retval = inputDialog(xmltvLst[select], key=xbmcgui.INPUT_ALPHANUM)
            if retval and len(retval) > 0:
                return retval
        else:
            return xmltvLst[select]            
            
def xmltvflePath(setting3):          
    xmlpath = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('xmltvLOC'), str(setting3) +'.xml'))
    if FileAccess.exists(xmlpath) == True:
        xmltvFle = xmlpath
    else:
        xmltvFle = setting3
    log("utils: xmltvflePath, xmltvFle = " + xmltvFle)  
    return xmltvFle

def setKodiRuntime(type,dbid,dur):
    if type == 'movie':
        set_Kodi_JSON('"method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : %s, "runtime" : %i }' %(str(dbid),int(dur)))
    elif type in ['episode','tvshow']:
        set_Kodi_JSON('"method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "runtime" : %i }' %(str(dbid),int(dur)))

def setKodiPlaycount(type,dbid,count):
    if type == 'movie':
        set_Kodi_JSON('"method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : %s, "playcount" : %i }' %(str(dbid),int(count)))
    elif type in ['episode','tvshow']:
        set_Kodi_JSON('"method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "playcount" : %i }' %(str(dbid),int(count)))

def EnableTrakt(val):
    log("utils: EnableTrakt")
    state = 'false'
    status = "Disabled"
    if val == True:
        state = 'true'
        status = "Enabled"
    OptNotify('Trakt %s'%status)
    set_Kodi_JSON('"method":"Addons.SetAddonEnabled","params":{"addonid":"script.trakt","enabled":%s}'%state)
    
def clearTraktScrob():
    clearProperty("script.trakt.ids")

def setTraktScrob():
    # Example code:
    # {u'tmdb': 264660}
    # {u'tvdb': 121361}
    # {u'imdb': u'tt0470752'}
    # {u'slug': u'ex-machina-2014'}
    # {u'trakt': 163375}
    # {u'tmdb': 264660, u'imdb': u'tt0470752', u'slug': u'ex-machina-2014', u'trakt': 163375}
    ids = ''
    id    = getProperty("OVERLAY.ID")
    dbid  = getProperty("OVERLAY.DBID")
    type  = getProperty("OVERLAY.Type")
    title = getProperty("OVERLAY.Title").replace('(',' ').replace(')','').replace(' ','-')

    # if content is not part of kodis db and has id scrob
    if (dbid == '0' or len(dbid) > 6) and id != '0':
        if type == 'movie':
            ids = json.dumps({u'imdb': id, u'slug': u'%s' %title})
        elif type == 'tvshow':
            ids = json.dumps({u'tvdb': id, u'slug': u'%s' %title})
        if ids:
            log("utils: setTraktScrob, trakt = " + str(ids))     
            setProperty('script.trakt.ids', ids)
            
def setTraktTag(pType='OVERLAY'):
    log("utils: setTraktTag")
    type = getProperty(("%s.Title")%pType)    
    if type == 'movie':
        media_type = 'movie'
    elif type == 'tvshow':
        media_type = 'show'
    else:
        return 
    dbid = getProperty(("%s.DBID")%pType)
    if dbid != '0' and len(dbid) < 6:
        xbmc.executebuiltin(("XBMC.RunScript(script.trakt,action=addtolist,list='PseudoTV_Live'[,media_type=%s,dbid=%s])") %(media_type,dbid))

def removeTraktTag(pType='OVERLAY'):
    log("utils: removeTraktTag")
    type = getProperty(("%s.Title")%pType)    
    if type == 'movie':
        media_type = 'movie'
    elif type == 'tvshow':
        media_type = 'show'
    else:
        return
    dbid = getProperty(("%s.DBID")%pType)
    if dbid != '0' and len(dbid) < 6:
        xbmc.executebuiltin(("XBMC.RunScript(script.trakt,action=removefromlist,list='PseudoTV_Live'[,media_type=%s,dbid=%s])") %(media_type,dbid))
    
def convert_to_float(frac_str):
    log("utils: convert_to_float")   
    try:
        return float(frac_str)
    except ValueError:
        num, denom = frac_str.split('/')
        try:
            leading, num = num.split(' ')
            whole = float(leading)
        except ValueError:
            whole = 0
        frac = float(num) / float(denom)
        return whole - frac if whole < 0 else whole + frac    

def convert_to_stars(val):
    log("utils: convert_to_stars")  
    return (val * 100 ) / 10
    
def datetime_to_epoch(dt):
    log("utils: datetime_to_epoch") 
    try:#sloppy fix, for threading issue with strptime.
        t = time.strptime(dt, '%Y-%m-%d %H:%M:%S')
    except:
        t = time.strptime(dt, '%Y-%m-%d %H:%M:%S')
    return time.mktime(t)
   
@cache_weekly   
def getJson(url):
    log("utils: getJson") 
    response = urllib2.urlopen(url)
    return json.load(response)
    
def makeTMPSTRdict(duration, title, year, subtitle, description, genre, type, id, thumburl, rating, hd, cc, stars, path):
    log("utils: makeTMPSTRdict") 
    # convert to dict for future channel building using ChannelList.dict2tmpstr()
    return {'duration':duration, 'title':title, 'year':year, 'subtitle':subtitle,'description':description,
            'genre':genre, 'type':type, 'id':id, 'thumburl':thumburl,
            'rating':rating, 'hd':hd, 'cc':cc, 'stars':stars, 'path':path}

def getSmartPlaylistName(fle):
    log("utils: getSmartPlaylistName") 
    fle = xbmc.translatePath(fle)

    try:
        xml = open(fle, "r")
    except:
        return ''

    try:
        dom = parse(xml)
    except:
        xml.close()
        return ''

    xml.close()

    try:
        plname = dom.getElementsByTagName('name')
        return plname[0].childNodes[0].nodeValue
    except:
        return ''  
        
def getChanPrefix(chantype, channame):
    log("utils: getChanPrefix") 
    if chantype == 0:
        newlabel = channame + " - Playlist"
    elif chantype == 5:
        newlabel = channame + " - Mixed"
    elif chantype in [1,3,6]:
        newlabel = channame + " - TV"
    elif chantype in [2,4]:
        newlabel = channame + " - Movies"
    elif chantype == 7:
        newlabel = channame + " - Directory" 
    elif chantype == 8:
        newlabel = channame + " - LiveTV"
    elif chantype == 9:
        newlabel = channame + " - InternetTV"
    elif chantype == 10:
        newlabel = channame + " - Youtube"            
    elif chantype == 11:
        newlabel = channame + " - RSS"            
    elif chantype == 12:
        newlabel = channame + " - Music"
    elif chantype == 13:
        newlabel = channame + " - Music Videos"
    elif chantype == 14:
        newlabel = channame + " - Exclusive"
    elif chantype == 15:
        newlabel = channame + " - Plugin"
    elif chantype == 16:
        newlabel = channame + " - UPNP"
    elif chantype == 9999:
        newlabel = ""
    else:
        newlabel = channame
    return newlabel
    
def patchFont():    
    log("utils: patchFont")
    import MyFont
    path = os.path.join(PTVL_SKIN_SELECT, 'script.pseudotv.live.fonts.xml')
    if FileAccess.exists(path):
        with open(path, 'rt') as f:
            tree = ElementTree.parse(f)
        for node in tree.findall('font'):
            try:
                if node.attrib.get('res') == MyFont.getSkinRes():
                    MyFont.addFont(node.attrib.get('name'), node.attrib.get('filename'), node.attrib.get('size'))
            except Exception,e:
                log('utils: patchFont, failed! ' + str(e))
                
def patchSeekbar():
    DSPath = xbmc.translatePath(os.path.join(XBMC_SKIN_LOC, 'DialogSeekBar.xml'))
    log("utils: patchSeekbar, DSPath = " + ascii(DSPath)) 
    #Patch dialogseekbar to ignore OSD for PTVL.
    found = False
    try:
        lineLST = file(DSPath, "r").readlines()   
        for i in range(len(lineLST)):
            patch = lineLST[i].find('<visible>Window.IsActive(fullscreenvideo) + !Window.IsActive(script.pseudotv.TVOverlay.xml) + !Window.IsActive(script.pseudotv.live.TVOverlay.xml)</visible>')
            if patch > 0:
                found = True
                
        if found == False:
            replaceAll(DSPath,'<window>','<window>\n\t<visible>Window.IsActive(fullscreenvideo) + !Window.IsActive(script.pseudotv.TVOverlay.xml) + !Window.IsActive(script.pseudotv.live.TVOverlay.xml)</visible>')
            xbmc.executebuiltin('XBMC.ReloadSkin()')
            log('utils: patchSeekbar, Patched dialogseekbar.xml')
    except Exception,e:
        log('utils: patchSeekbar, Failed! ' + str(e))

def egTrigger_Thread(message, sender):
    log("egTrigger_Thread")
    json_query = ('{"jsonrpc": "2.0", "method": "JSONRPC.NotifyAll", "params": {"sender":"%s","message":"%s"}, "id": 1}' % (sender, message))
    sendJSON(json_query)
       
def egTrigger(message, sender='PTVL'):
    log("egTrigger")
    try:
        egTriggerTimer = threading.Timer(0.5, egTrigger_Thread, [message, sender])      
        if egTriggerTimer.isAlive():
            egTriggerTimer.cancel()
        egTriggerTimer = threading.Timer(0.5, egTrigger_Thread, [message, sender])
        egTriggerTimer.name = "egTriggerTimer"   
        egTriggerTimer.start() 
    except Exception,e:
        log('utils: egTrigger, failed! ' + str(e))  
        
def getChanTypeLabel(chantype):
    if chantype == 0:
        return "Custom Playlist"
    elif chantype == 1:
        return "TV Network"
    elif chantype == 2:
        return "Movie Studio"
    elif chantype == 3:
        return "TV Genre"
    elif chantype == 4:
        return "Movie Genre"
    elif chantype == 5:
        return "Mixed Genre"
    elif chantype == 6:
        return "TV Show"
    elif chantype == 7:
        return "Directory"
    elif chantype == 8:
        return "LiveTV"
    elif chantype == 9:
        return "InternetTV"
    elif chantype == 10:
        return "Youtube"
    elif chantype == 11:
        return "RSS"
    elif chantype == 12:
        return "Music"
    elif chantype == 13:
        return "Music Videos (Coming Soon)"
    elif chantype == 14:
        return "Exclusive (Coming Soon)"
    elif chantype == 15:
        return "Plugin"
    elif chantype == 16:
        return "UPNP"
    return 'None'
    
# Adapted from tria http://forum.kodi.tv/showthread.php?tid=201627
# addonId is the Addon ID
# id1 is the Category (Tab) offset (0=first, 1=second, 2...etc)
# id2 is the Setting (Control) offse (0=first, 1=second, 2...etc)
# Example: OpenAddonSettings('plugin.video.name', 2, 3)
# This will open settings dialog focusing on fourth setting (control) inside the third category (tab)

def openAddonSettings(addonId, id1=None, id2=None, ret=True):
    xbmc.executebuiltin('Addon.OpenSettings(%s)' % addonId)
    if id1 != None:
        xbmc.executebuiltin('SetFocus(%i)' % (id1 + 60000))
    if id2 != None:
        xbmc.executebuiltin('SetFocus(%i)' % (id2 + 100))
    if ret == True:
        REAL_SETTINGS.openSettings()