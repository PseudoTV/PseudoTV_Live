#  Much of this code was taken from existing Log Uploaders but so far
#  I have been unable to find details of the original author(s) to credit them.
#  Changes in the code have been made by myself, notably the checks to see if the system
#  is XBMC or Kodi.
#
#      Copyright (C) 2016 whufclee, Kevin S. Graer
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import xbmcaddon, xbmcgui
import os, re, json, urllib, urllib2

from resources.lib.Globals import *
from resources.lib.utils import *
from xbmc import getCondVisibility as condition, translatePath as translate, log as xbmc_log

STRINGS = {
    'do_upload': 30000,
    'upload_id': 30001,
    'upload_url': 30002,
    'no_email_set': 30003,
    'email_sent': 30004
}
BASE_URL = 'http://xbmclogs.com'
UPLOAD_LINK = BASE_URL + '/%s'
UPLOAD_URL = BASE_URL + '/api/json/create'
EMAIL_URL = BASE_URL + '/xbmc-addon.php'

REPLACES = (
    ('//.+?:.+?@', '//USER:PASSWORD@'),
    ('<user>.+?</user>', '<user>USER</user>'),
    ('<pass>.+?</pass>', '<pass>PASSWORD</pass>'),
)

class LogUploader(object):

    def __init__(self):
        self.__log('started')
        self.get_settings()
        found_logs = self.__get_logs()
        uploaded_logs = []
        
        for logfile in found_logs:
            
            if self.ask_upload(logfile['title']):
                paste_id = self.upload_file(logfile['path'])
                
                if paste_id:
                    uploaded_logs.append({
                        'paste_id': paste_id,
                        'title': logfile['title']
                    })
                    self.report_msg(paste_id)
        
        if uploaded_logs and self.email_address:
            self.report_mail(self.email_address, uploaded_logs)
            pass

    def get_settings(self):
        self.email_address = REAL_SETTINGS.getSetting('email')
        if not self.email_address:
            self.email_address = inputDialog('Enter Email', key=xbmcgui.INPUT_ALPHANUM)
            REAL_SETTINGS.setSetting('email',self.email_address)
                
        self.__log('uploadLog: len(email)=%d' % len(self.email_address))
        self.skip_oldlog = REAL_SETTINGS.getSetting('skip_oldlog') == 'true'
        self.__log('uploadLog: skip_oldlog=%s' % self.skip_oldlog)
            
    def upload_file(self, filepath):
        self.__log('reading log...')
        file_content = open(filepath, 'r').read()
        
        for pattern, repl in REPLACES:
            file_content = re.sub(pattern, repl, file_content)
        
        self.__log('starting upload "%s"...' % filepath)
        post_dict = {
            'data': file_content,
            'project': 'www',
            'language': 'text',
            'expire': 1209600,
        }        
        try:
            post_data = json.dumps(post_dict)
            headers = {
                'User-Agent': '%s-%s' % (ADDON_NAME, ADDON_VERSION),
                'Content-Type': 'application/json',
            }
            req      = urllib2.Request(UPLOAD_URL, post_data, headers)
            response = urllib2.urlopen(req).read()
            self.__log('upload done.')

            response_data = json.loads(response)
        
        except:
            response_data = None
        
        if response_data and response_data.get('result', {}).get('id'):
            paste_id = response_data['result']['id']
            self.__log('paste_id=%s' % paste_id)
            return paste_id
        
        else:
            self.__log('upload failed with response: %s' % repr(response))

    def ask_upload(self, logfile):
        Dialog = xbmcgui.Dialog()
        msg1 = 'Do you want to upload "%s"?' % logfile
        
        if self.email_address:
            msg2 = 'Email will be sent to: %s' % self.email_address
        
        else:
            msg2 = 'No email will be sent (No email is configured)'
        
        return Dialog.yesno(ADDON_NAME, msg1, '', msg2)

    def report_msg(self, paste_id):
        url = UPLOAD_LINK % paste_id
        Dialog = xbmcgui.Dialog()
        msg1 = 'Uploaded with ID: [B]%s[/B]' % paste_id
        msg2 = 'URL: [B]%s[/B]' % url
        return Dialog.ok(ADDON_NAME, msg1, '', msg2)

    def report_mail(self, mail_address, uploaded_logs):
        if not mail_address:
            raise Exception('No Email set!')
        
        post_dict = {'email': mail_address}
        
        for logfile in uploaded_logs:
            
            if logfile['title'] == 'kodi.log':
                post_dict['xbmclog_id'] = logfile['paste_id']
            
            elif logfile['title'] == 'kodi.old.log':
                post_dict['oldlog_id'] = logfile['paste_id']
            
            elif logfile['title'] == 'crash.log':
                post_dict['crashlog_id'] = logfile['paste_id']
        
        post_data = urllib.urlencode(post_dict)
        
        if DEBUG:
            print post_data
        
        req      = urllib2.Request(EMAIL_URL, post_data)
        response = urllib2.urlopen(req).read()
        
        if DEBUG:
            print response

    def __get_logs(self):
        xbmc_version    = xbmc.getInfoLabel("System.BuildVersion")
        version         = float(xbmc_version[:4])
        log_path        = translate('special://logpath')
        crashlog_path   = None
        crashfile_match = None
        
        if condition('system.platform.osx') or condition('system.platform.ios'):
            crashlog_path = os.path.join(
                os.path.expanduser('~'),
                'Library/Logs/CrashReporter'
            )
            
            if version < 14:
                crashfile_match = 'XBMC'
            
            else:
                crashfile_match = 'kodi'
        
        elif condition('system.platform.windows'):
            crashlog_path = log_path
            crashfile_match = '.dmp'
        
        elif condition('system.platform.linux'):
            crashlog_path = os.path.expanduser('~')
            
            if version < 14:
                crashfile_match = 'xbmc_crashlog'
            
            else:
                crashfile_match = 'kodi_crashlog'

# get fullpath for xbmc.log and xbmc.old.log
        if version < 14:
            log = os.path.join(log_path, 'xbmc.log')
            log_old = os.path.join(log_path, 'xbmc.old.log')
        
        else:
            log = os.path.join(log_path, 'kodi.log')
            log_old = os.path.join(log_path, 'kodi.old.log')

# check for XBMC crashlogs
        log_crash = None
        
        if crashlog_path and os.path.isdir(crashlog_path) and crashfile_match:
            crashlog_files = [s for s in os.listdir(crashlog_path)
                              
                              if os.path.isfile(os.path.join(crashlog_path, s))
                              and crashfile_match in s]
            
            if crashlog_files:
                # we have crashlogs, get fullpath from the last one by time
                crashlog_files = self.__sort_files_by_date(crashlog_path,
                                                           crashlog_files)
                log_crash = os.path.join(crashlog_path, crashlog_files[-1])
        
        found_logs = []
        
        if os.path.isfile(log):
            
            if version < 14:
                found_logs.append({
                    'title': 'xbmc.log',
                    'path': log
                })
            
            else:
                found_logs.append({
                    'title': 'kodi.log',
                    'path': log
                })
        
        if log_crash and os.path.isfile(log_crash):
            found_logs.append({
                'title': 'crash.log',
                'path': log_crash
            })
        
        return found_logs

    def __sort_files_by_date(self, path, files):
        files.sort(key=lambda f: os.path.getmtime(os.path.join(path, f)))
        return files

    def __log(self, msg):
        xbmc_log(u'%s: %s' % (ADDON_NAME, msg))


def _(string_id):
    if string_id in STRINGS:
        return REAL_SETTINGS.getLocalizedString(STRINGS[string_id])
    
    else:
        xbmc_log('String is missing: %s' % string_id)
        return string_id


if __name__ == '__main__':
    show_busy_dialog()
    Uploader = LogUploader()
    hide_busy_dialog()