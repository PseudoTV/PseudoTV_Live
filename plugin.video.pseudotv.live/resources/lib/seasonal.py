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

from globals     import *
from seasons     import *

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

    def getMonth(self):
        """
        Retrieves the current month as a full name (e.g., "January").

        :return: The name of the current month.
        """
        return datetime.datetime.now().strftime('%B')

    def getWeek(self):
        """
        Calculates the current week of the month based on the adjusted day of the month.
        Weeks are determined by dividing the adjusted day of the month by 7.

        :return: The current week of the month as an integer (1 to 5).
        """
        dt = datetime.datetime.now()
        adjusted_dom = dt.day + dt.replace(day=1).weekday()
        week = (adjusted_dom / 7.0)
        if week < 1 or week > 4:
            return int(ceil(week))
        else:
            return int(floor(week))

    @cacheit(expiration=datetime.timedelta(minutes=5), checksum=PROPERTIES.getInstanceID())
    def getHoliday(self, nearest=SETTINGS.getSettingBool('Nearest_Holiday')):
        """
        Retrieves the current or nearest holiday based on user settings.

        :param nearest: Boolean indicating whether to return the nearest holiday (default: True).
        :return: A dictionary representing the holiday details.
        """
        self.log('getHoliday, nearest = %s' % (nearest))
        if nearest:
            return self.getNearestHoliday()
        else:
            return self.getCurrentHoliday()

    def getCurrentHoliday(self):
        """
        Retrieves the holiday for the current month and week.

        :return: A dictionary representing the holiday details for the current month and week.
        """
        return SEASONS.get(self.getMonth(), {}).get(self.getWeek(), {})

    def getNearestHoliday(self, fallback=True):
        """
        Retrieves the nearest holiday. If no holiday is found in the current week, it searches
        forward and optionally backward for the nearest holiday.

        :param fallback: Boolean indicating whether to search backward if no holiday is found forward (default: True).
        :return: A dictionary representing the nearest holiday.
        """
        holiday = {}
        month = self.getMonth()
        week = self.getWeek()
        weeks = [1, 2, 3, 4, 5][week - 1:]  # Running a 5-week month for extended weeks > 28 days.
        if fallback:
            past = [1, 2, 3, 4, 5][:week - 1]
            past.reverse()
            weeks = weeks + past
        for next in weeks:
            holiday = SEASONS.get(month, {}).get(str(next), {})
            if holiday.get('keyword'):
                break
        self.log('getNearestHoliday, using fallback = %s, month = %s, week = %s, nearest week = %s, returning = %s' %
                 (fallback, month, week, next, holiday))
        return holiday

    def buildSeasonal(self):
        """
        Builds a generator that provides seasonal content queries. Each query is augmented
        with holiday-specific metadata, including sorting and filtering options.

        :yield: A dictionary representing a seasonal content query.
        """
        self.log('buildSeasonal')
        season = self.getHoliday()
        for query in season.get('query', []):
            for param in KEYWORDS.get(season.get('keyword', {}), {}).get(query.get('key', {}), {}):
                item = query.copy()
                holiday = season.copy()
                holiday.pop("query")
                item["holiday"] = holiday
                item_sort = SORT.copy()
                if param.get("sort"):
                    item_sort.update(param.get("sort"))
                item["sort"] = item_sort
                if param.get("filter"):
                    item["filter"] = param.get("filter")
                yield item