#   Copyright (C) 2024 Lunatixz
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

# https://www.holidaysmart.com/holidays/daily/fandom
# https://www.holidaysmart.com/holidays/daily/tv-movies
           
from globals     import *

TV_QUERY    = {"path":"videodb://tvshows/titles/" ,"limits":{},"sort":{},"filter":{},
               "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"}
               
MOVIE_QUERY = {"path":"videodb://movies/titles/"  ,"limits":{},"sort":{},"filter":{},
               "method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie"  ,"key":"movies"}
    
FILTER      = {"field":"","operator":"","value":[]}
SORT        = {"method":"","order":"","ignorearticle":True,"useartistsortname":True}
KEY_QUERY   = {"method":"","order":"","field":'',"operator":'',"value":[]}

class Seasonal:
    def __init__(self):
        """
        Initializes the Seasonal class. Sets up logging and caching.
        """
        self.log('__init__')
        self.cache = SETTINGS.cacheDB

    def log(self, msg, level=xbmc.LOGDEBUG):
        """
        Logs a message to the system log with the specified logging level.

        :param msg: The message to log.
        :param level: The log level (default: xbmc.LOGDEBUG).
        """
        return log('%s: %s' % (self.__class__.__name__, msg), level)

    def getYear(self):
        """
        Get the current year.

        This function retrieves the current year using the `datetime` module.

        returns:
        int: The current year.
        """
        return datetime.datetime.now().year

    def getMonth(self, name=False):
        """
        Get the current month in either name or numeric format.

        Args:
            name (bool): If True, returns the full name of the current month (e.g., 'April').
                         If False, returns the numeric representation of the current month (e.g., 4).

        Returns:
            str/int: The current month as a string (full name) or as an integer (numeric format).
        """
        if name: return datetime.datetime.now().strftime('%B')  # Full month name
        else:    return datetime.datetime.now().month  # Numeric month

    def getWeek(self):
        """
        Calculates the current week of the month based on the adjusted day of the month.
        Weeks are determined by dividing the adjusted day of the month by 7.

        :return: The current week of the month as an integer (1 to 5).
        """
        dt = datetime.datetime.now()
        adjusted_dom = self.getDay()
        week = (adjusted_dom / 7.0)
        if week < 1 or week > 4: return int(ceil(week))
        else:                    return int(floor(week))

    def getDay(self):
        """
        Calculate and return the adjusted day of the month.

        This function adds the current day of the month to the weekday of the first day of the current month.
        The result can be used to determine the week number or other date-based calculations.

        Returns:
            int: Adjusted day of the month.
        """
        dt = datetime.datetime.now()
        return dt.day + dt.replace(day=1).weekday() - 1

    def getDOM(self, year, month):
        """
        Get all days of the specified month for a given year.

        This function uses the `calendar.Calendar` class to iterate through all days of the specified month and year.
        It extracts only the valid days (ignoring placeholder zeros for days outside the month) and returns them as a list.

        Args:
            year (int): The year of the desired month.
            month (int): The month (1-12) for which to retrieve the days.

        Returns:
            list: A list of integers representing the days in the specified month.
        """
        cal = calendar.Calendar()
        days_in_month = []
        for day in cal.itermonthdays2(year, month):
            if day[0] != 0:  # Exclude placeholder days (zeros)
                days_in_month.append(day[0])
        return days_in_month

    # @cacheit(expiration=datetime.timedelta(minutes=15), checksum=PROPERTIES.getInstanceID())
    def getSeason(self, key):
        self.log('getSeason, key = %s' % (key))
        return getJSON(HOLIDAYS).get(key,{})

    # @cacheit(expiration=datetime.timedelta(minutes=15), checksum=PROPERTIES.getInstanceID())
    def getSeasons(self, month):
        self.log('getSeasons, month = %s' % (month))
        return getJSON(SEASONS).get(month,{})

    @cacheit(expiration=datetime.timedelta(minutes=15), checksum=PROPERTIES.getInstanceID())
    def getHoliday(self, nearest=SETTINGS.getSettingBool('Nearest_Holiday')):
        """
        Retrieves the current or nearest holiday based on user settings.

        :param nearest: Boolean indicating whether to return the nearest holiday (default: True).
        :return: A dictionary representing the holiday details.
        """
        self.log('getHoliday, nearest = %s' % (nearest))
        if nearest: return self.getNearestHoliday()
        else:       return self.getCurrentHoliday()

    def getCurrentHoliday(self):
        """
        Retrieves the holiday for the current month and week.

        :return: A dictionary representing the holiday details for the current month and week.
        """
        return self.getSeasons(self.getMonth(name=True)).get(self.getDay(),{})

    def getNearestHoliday(self, fallback=True):
        """
        Retrieves the nearest holiday. If no holiday is found in the current week, it searches
        forward and optionally backward for the nearest holiday.

        :param fallback: Boolean indicating whether to search backward if no holiday is found forward (default: True).
        :return: A dictionary representing the nearest holiday.
        """
        holiday = {}
        month = self.getMonth(name=True)
        day   = self.getDay()
        dom   = self.getDOM(self.getYear(),self.getMonth())
        curr  = dom[day - 1:] # Running a 5-week month for extended weeks > 28 days
        days  = curr
        if fallback:
            past = dom[:day - 1]
            past.reverse()
            days = days + past
            
        for next in days:
            holiday = self.getSeasons(month).get(str(next),{})
            if holiday.get('keyword'): break
        self.log('getNearestHoliday, using fallback = %s, month = %s, day = %s, nearest day = %s, returning = %s' %(fallback, month, day, next, holiday))
        return holiday

    def buildSeasonal(self):
        """
        Builds a generator that provides seasonal content queries. Each query is augmented
        with holiday-specific metadata, including sorting and filtering options.

        :yield: A dictionary representing a seasonal content query.
        """
        holiday = self.getHoliday()
        season  = self.getSeason(holiday.get('keyword'))
        for type, params in list(season.items()):
            for param in params:
                item = {'episodes':TV_QUERY,'movies':MOVIE_QUERY}[type.lower()].copy()
                item["holiday"] = holiday
                
                item_sort = SORT.copy()
                if param.get("sort"): item_sort.update(param.get("sort"))
                item["sort"] = item_sort
                
                item_filter = FILTER.copy()
                if param.get("filter"): item_filter.update(param.get("filter"))
                item["filter"] = item_filter
                
                self.log('buildSeasonal, %s - item = %s'%(holiday.get('name'),item))
                yield item
       