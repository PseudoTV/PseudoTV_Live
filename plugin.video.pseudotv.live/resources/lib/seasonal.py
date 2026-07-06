#   Copyright (C) 2026 Lunatixz
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
# Adapted from https://github.com/sualfred/script.embuary.helper/blob/matrix

# https://www.holidaysmart.com/category/fandom
# https://www.holidaysmart.com/holidays/daily/fandom
# https://www.holidaysmart.com/holidays/daily/tv-movies
# https://tvtropes.org/pmwiki/pmwiki.php/Main/PopCultureHoliday
# https://fanlore.org/wiki/List_of_Annual_Holidays,_Observances,_and_Events_in_Fandom

from variables   import *
from cache       import Cache, cacheit

KEY_QUERY   = {"method":"","order":"","field":'',"operator":'',"value":[]}
LIMITS      = {"end":-1,"start":0,"total":0}
FILTER      = {"field":"","operator":"","value":[]}
SORT        = {"method":"","order":"","ignorearticle":True,"useartistsortname":True}
TV_QUERY    = {"path":"videodb://tvshows/titles/", "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes","limits":LIMITS,"sort":SORT,"filter":FILTER}
MOVIE_QUERY = {"path":"videodb://movies/titles/" , "method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie"  ,"key":"movies"  ,"limits":LIMITS,"sort":SORT,"filter":FILTER}

class Seasonal(object):
    def __init__(self, service=None):
        if service is None:
            from kodi import _get_Service
            service = _get_Service()
        self.service = service
        self.pool    = service.pool
        self.cache   = service.cache


    def log(self, msg, level=xbmc.LOGDEBUG):
        LOG('%s: %s' % (self.__class__.__name__, msg), level)


    def getYear(self):
        return datetime.datetime.now().year


    def getMonth(self, name=False):
        if name: return datetime.datetime.now().strftime('%B')  # Full month name
        else:    return datetime.datetime.now().month           # Numeric month


    def getDay(self):
        return datetime.datetime.now().day


    def getDOM(self, year, month):
        cal = calendar.Calendar()
        days_in_month = []
        for day in cal.itermonthdays2(year, month):
            if day[0] != 0:  # Exclude placeholder days (zeros)
                days_in_month.append(day[0])
        return days_in_month


    def getSeason(self, key):
        self.log('getSeason, key = %s' % (key))
        return FileAccess.getJSON(HOLIDAYS).get(key,{})


    def getSeasons(self, month):
        self.log('getSeasons, month = %s' % (month))
        return FileAccess.getJSON(SEASONS).get(month,{})


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def getHoliday(self, nearest=None):
        if nearest is None:
            nearest = Globals.settings.getSettingBool('Nearest_Holiday')
        self.log('getHoliday, nearest = %s' % (nearest))
        if nearest: return self.getNearestHoliday()
        else:       return self.getCurrentHoliday()


    def getCurrentHoliday(self):
        return self.getSeasons(self.getMonth(name=True)).get(self.getDay(),{})


    def getSpecialHolidays(self, month, day): #todo check if month, day of week, day match holiday exceptions.
        return {"Friday":{"13":{ "name": "Friday The 13th", "tagline": "", "keyword": "", "logo": ""}}}
    

    def getNearestHoliday(self, fallback=True):
        holiday = {}
        month = self.getMonth(name=True)
        day   = self.getDay()
        dom   = self.getDOM(self.getYear(),self.getMonth())
        curr  = dom[day - 1:]
        days  = curr
        if fallback:
            past = dom[:day - 1]
            past.reverse()
            days = days + past
            
        season = self.getSeasons(month)
        for next in days:
            holiday = season.get(str(next),{})
            if holiday.get('keyword'): break
        self.log('getNearestHoliday, using fallback = %s, month = %s, day = %s, nearest day = %s, returning = %s' %(fallback, month, day, next, holiday))
        return holiday


    def buildSeasonal(self, holiday=None):
        if holiday is None: holiday = self.getHoliday()
        season  = self.getSeason(holiday.get('keyword'))
        for type, params in list(season.items()):
            for param in params:
                item = {'episodes':TV_QUERY,'movies':MOVIE_QUERY}[type.lower()].copy()
                item["holiday"] = holiday
                item["sort"].update(param.get("sort"))
                item["filter"].update(param.get("filter"))
                self.log('buildSeasonal, %s - item = %s'%(holiday.get('name'),item))
                yield item
       
