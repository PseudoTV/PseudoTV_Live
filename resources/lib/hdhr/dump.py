#-------------------------------------------------------------------------------
# Simple Tool to dump the Rules List from the HDHR DVR
#
#########
#
#-------------------------------------------------------------------------------
import os
import platform
import logging
import sys
import json
import urllib
import time
from time import strftime


class HDHomeRun:
	def __init__(self, hdhr_data):
		self.isHttpDVR = False
		self.hdhr_base = hdhr_data['BaseURL']
		self.hdhr_discover = hdhr_data['DiscoverURL']
		self.hdhr_lineup = hdhr_data['LineupURL']
		if self.hdhr_discover != None:
			self.isHttpDVR = True
			response = urllib.urlopen(self.hdhr_discover)
			data = json.loads(response.read())
			self.hdhr_auth = data['DeviceAuth']
			self.hdhr_id = data['DeviceID']
			self.hdhr_model = data['ModelNumber']

	def getModel(self):
		if self.isHttpDVR:
			return self.hdhr_model
		else:
			return 'Not HHTP DVR'

	def getID(self):
		if self.isHttpDVR:
			return self.hdhr_id
		else:
			return 'Not HHTP DVR'

	def getAuth(self):
		if self.isHttpDVR:
			return self.hdhr_auth
		else:
			return 'Not HHTP DVR'

	def isHttpDvr(self):
		return self.isHttpDVR


def discoverHDHRList():
    authStr = ''
    try:
        url = 'http://ipv4.my.hdhomerun.com/discover'
        response = urllib.urlopen(url)
        data = json.loads(response.read())
        hdhrs_found = len(data)
        print 'found ' + str(hdhrs_found) + ' HDHomerun devices'
        for hdhr_info in data:
            hdhr_entry = HDHomeRun(hdhr_info)
            if hdhr_entry.isHttpDvr():
                print 'Found' + \
                    ' ' + hdhr_entry.getModel() + \
                    ' ' + hdhr_entry.getID() + \
                    ' ' + hdhr_entry.getAuth()
                authStr += hdhr_entry.getAuth()
        print 'final authstr ' + authStr
        recordings_url = 'http://my.hdhomerun.com/api/recording_rules?DeviceAuth=' + authStr
        response = urllib.urlopen(recordings_url)
        recordings = json.loads(response.read())
        if not recordings:
             return authStr
        for recording in recordings:
            recentOnly = False
            if 'RecentOnly' in recording:
                recentOnly = True
            if 'AfterOriginalAirdateOnly' in recording:
                airdate = 0
            if 'ChannelOnly' in recording:
                channelOnly = 0
            print 'RecordingRuleID: ' + recording['RecordingRuleID'] +\
                ' SeriesID: ' + recording['SeriesID'] + \
                ' StartPadding: ' + str(recording['StartPadding']) + \
                ' EndPadding: ' + str(recording['EndPadding']) + \
                ' Priority: ' + str(recording['Priority']) + \
                ' RecentOnly: ' + str(recentOnly) + \
                ' Title: ' + str(recording['Title'])
    except:
        pass
    return authStr