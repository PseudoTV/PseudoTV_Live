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

from Globals import *

class PVR:

    def __init__(self): 
        print '__init__'
        self.Reminder = SETTINGS_LOC + '/' + 'reminders.ini'
        
        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('PVR: ' + msg, level)

    
    def logDebug(self, msg, level = xbmc.LOGDEBUG):
        if isDebug() == True:
            log('PVR: ' + msg, level)
            
    def SetReminder(self):
        print 'setreminder'
        # set reminder
        
    def isReminder(self):
        print 'isReminder'
        #return bool if show has reminder set
        
    def CheckReminder(self):
        print 'checkreminder'
        #check if more titles on set channel match set title.
        
    def RemoveReminder(self):
        print 'Removereminder'
        # remove reminder
        
    def NextReminder(self):
        print 'queryreminder'
        # find upcoming reminder







# import os, sys
# import SimpleDownloader as downloader
# from Globals import *

# addon_id = 'script.pseudotv.live'
# downloader = downloader.SimpleDownloader()
    
# def PVRrecord(chtype, path, folder, name):
    # print 'PVRrecord'
        
    # if path[0:3] == 'pvr':
        # #trigger pvr backend download
        # self.log('PVRrecord') 
    # elif path[0:4] == 'http':
        # self.log('PVRrecord, http')
        # downloadFile(path, folder, name)
    # elif path[0:4] == 'rtmp':
        # self.log('PVRrecord, rtmp')
        # downloadFile(path, folder, name)
    # elif path[0:29] == 'plugin://plugin.video.youtube':
        # self.log('PVRrecord, youtube') 
        # videoid = path.split('/')[5]
        # videoid = videoid.split('videoid=')[1]
        # # videoid = 'http://www.youtube.com/v/' + videoid
        # downloadFile(videoid, folder, name)
        # #json query plugin link for real url or query xbmc.player for playing url            
      
        # # A simple RTMP Live download
         # # video = {"url": "rtmp://aljazeeraflashlivefs.fplive.net:1935/aljazeeraflashlive-live/aljazeera_english_1", "download_path": "/tmp", "Title": "Live Download", "live": "true", "duration": "10"}
         # # downloader.download("aljazeera-10minutes.mp4", params)
         
        # # get url from player (use in overlay)
        # # self.common.log("path: " + repr(download_path))
        # # (video, status) = self.player.buildVideoObject(params)

        # # if "video_url" in video and download_path:
            # # params["Title"] = video['Title']
            # # params["url"] = video['video_url']
            # # params["download_path"] = download_path
            # # filename = "%s-[%s].mp4" % (''.join(c for c in video['Title'] if c not in self.utils.INVALID_CHARS), video["videoid"])

            # # self.subtitles.downloadSubtitle(video)
            # # if get("async"):
                # # self.downloader.download(filename, params, async=False)
            # # else:
                # # self.downloader.download(filename, params)
                
                # # def downloadVideo(self, params):
        # # get = params.get
        # # self.common.log(repr(params))
        # # if not self.settings.getSetting("download_path"):
            # # self.common.log("Download path missing. Opening settings")
            # # self.utils.showMessage(self.language(30600), self.language(30611))
            # # self.settings.openSettings()

        # # download_path = self.settings.getSetting("download_path")
        # # if not download_path:
            # # return

        # # self.common.log("path: " + repr(download_path))
        # # (video, status) = self.player.buildVideoObject(params)

        # # if "video_url" in video and download_path:
            # # params["Title"] = video['Title']
            # # params["url"] = video['video_url']
            # # params["download_path"] = download_path
            # # filename = "%s-[%s].mp4" % (''.join(c for c in video['Title'] if c not in self.utils.INVALID_CHARS), video["videoid"])

            # # self.subtitles.downloadSubtitle(video)
            # # if get("async"):
                # # self.downloader.download(filename, params, async=False)
            # # else:
                # # self.downloader.download(filename, params)
        # # else:
            # # if "apierror" in video:
                # # self.utils.showMessage(self.language(30625), video["apierror"])
            # # else:
                # # self.utils.showMessage(self.language(30625), "ERROR") 
                
# def downloadFile(url, folder, name):
    # print 'downloadFile'
    # print url, folder
    # download_folder = REAL_SETTINGS.getSetting("PVR_Folder")
    # if download_folder == '':
        # addon.show_small_popup(title='File Not Downloadable', msg='You need to set your download folder in addon settings first', delay=int(5000), image=THUMB)
    # else:     
        # download_folder = os.path.join(download_folder, folder)
        # if not os.path.exists(download_folder):
             # os.makedirs(download_folder)
        # # if resolvable(url):
            # # url = resolve(url)
            # # ext = ''
            # # if '.mp4' in url:
                # # ext = '.mp4'
            # # elif '.flv' in url:
                # # ext = '.flv'
            # # elif '.avi' in url:
                # # ext = '.avi'
            # # if not ext == '':
        # ext = '.mp4'
        # params = {"url":url, "download_path":download_folder}
        # downloader.download(name + ext, params)
            # # else:
                # # addon.show_small_popup(title='Can Not Download File', msg='Unsupported Host', delay=int(5000), image=THUMB)
        # # else:
            # # addon.show_small_popup(title='Can Not Download File', msg='Unable To Resolve Url', delay=int(5000), image=THUMB)
                          
