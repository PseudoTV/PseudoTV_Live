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

import copy
from typing import List, Dict, Optional, Union, Generator, Any

from variables    import *
from _services    import _Service
from cache        import Cache, cacheit

KEY_QUERY   = {"method":"","order":"","field":'',"operator":'',"value":[]}
LIMITS      = {"end":-1,"start":0,"total":0}
FILTER      = {"field":"","operator":"","value":[]}
SORT        = {"method":"","order":"","ignorearticle":True,"useartistsortname":True}
TV_QUERY    = {"path":"videodb://tvshows/titles/", "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes","limits":LIMITS,"sort":SORT,"filter":FILTER}
MOVIE_QUERY = {"path":"videodb://movies/titles/" , "method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie"  ,"key":"movies"  ,"limits":LIMITS,"sort":SORT,"filter":FILTER}

class Seasonal(object):


    def __init__(self, service: Optional[_Service] = None):
        if service is None: service = _Service()
        self.service = service
        self.pool    = service.pool
        self.cache   = service.cache


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s' % (self.__class__.__name__, msg), level)


    def getYear(self) -> int:
        return datetime.datetime.now().year


    def getMonth(self, name: bool = False) -> Union[str, int]:
        if name: return datetime.datetime.now().strftime('%B')  # Full month name
        else:    return datetime.datetime.now().month           # Numeric month


    def getDay(self) -> int:
        return datetime.datetime.now().day


    def getDOM(self, year: int, month: int) -> List[int]:
        cal = calendar.Calendar()
        days_in_month = []
        for day in cal.itermonthdays2(year, month):
            if day[0] != 0:  # Exclude placeholder days (zeros)
                days_in_month.append(day[0])
        return days_in_month


    def getSeason(self, key: str) -> Dict[str, Any]:
        self.log('getSeason, key = %s' % (key))
        return self.getHolidaysData().get(key,{})


    def getSeasons(self, month: str) -> Dict[str, Any]:
        self.log('getSeasons, month = %s' % (month))
        return self.getSeasonsData().get(month,{})


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def getHoliday(self, nearest: Optional[bool] = None) -> Dict[str, Any]:
        if nearest is None:
            nearest = Globals.settings.getSettingBool('Nearest_Holiday')
        self.log('getHoliday, nearest = %s' % (nearest))
        if nearest: return self.getNearestHoliday()
        else:       return self.getCurrentHoliday()


    def getCurrentHoliday(self) -> Dict[str, Any]:
        return self.getSeasons(self.getMonth(name=True)).get(self.getDay(),{})


    def getSpecialHolidays(self, month: str, day: str) -> Dict[str, Any]: #todo check if month, day of week, day match holiday exceptions.
        return {"Friday":{"13":{ "name": "Friday The 13th", "tagline": "", "keyword": "", "logo": ""}}}
    


    def getNearestHoliday(self, fallback: bool = True) -> Dict[str, Any]:
        """Find the nearest holiday with a keyword, optionally wrapping to previous days."""
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


    # ---- CRUD for the seasonal/holiday JSON data ----------------------------
    # Mirrors the Channels pattern: seed from the shipped default file, then all
    # user edits persist to a version-keyed cache setting (writable cache.db in
    # the profile dir). Reads fall back to the default when no user copy exists;
    # writes NEVER touch REMOTE_LOC, so an addon update can't wipe amendments.

    def getSeasonsData(self) -> Dict[str, Any]:
        """Return the full seasons.json: {month: {day: {name, tagline, keyword, logo}}}."""
        return self._getMetaData(SEASONS_KEY, SEASONS)

    def getHolidaysData(self) -> Dict[str, Any]:
        """Return the full holidays.json: {keyword: {episodes: [...], movies: [...]}}."""
        return self._getMetaData(HOLIDAYS_KEY, HOLIDAYS)

    def setSeasonsData(self, data: Dict[str, Any]) -> bool:
        """Persist the full seasons.json to the user cache setting (never REMOTE_LOC)."""
        ok = Globals.settings.setCacheSetting(SEASONS_KEY, data, FileAccess._getMD5(SEASONS_KEY), life=-1)
        self._seedMeta(SEASONS_KEY, SEASONS)
        return ok

    def setHolidaysData(self, data: Dict[str, Any]) -> bool:
        """Persist the full holidays.json to the user cache setting (never REMOTE_LOC)."""
        ok = Globals.settings.setCacheSetting(HOLIDAYS_KEY, data, FileAccess._getMD5(HOLIDAYS_KEY), life=-1)
        self._seedMeta(HOLIDAYS_KEY, HOLIDAYS)
        return ok

    def _seedMeta(self, key: str, master_fle: str):
        """Record the shipped master snapshot as the merge base so a later master
        update can adopt defaults the user didn't customize."""
        try:
            master = FileAccess.getJSON(master_fle) or {}
            Globals.settings.setCacheSetting('%s.meta' % key, {'prev': master},
                                             FileAccess._getMD5('%s.meta' % key), life=-1)
        except Exception as e:
            self.log('_seedMeta, %s failed: %s' % (key, e), xbmc.LOGDEBUG)

    def _getMetaData(self, key: str, master_fle: str) -> Dict[str, Any]:
        """Return the user cache for `key`, merged when the shipped master changed.

        Uses the snapshot recorded at save time (via _seedMeta) as the 3-way base:
        entries the user left at their default adopt the new master meta, user edits
        are preserved, and brand-new master entries are added. Never writes REMOTE_LOC.
        """
        master = FileAccess.getJSON(master_fle) or {}
        user = Globals.settings.getCacheSetting(key, FileAccess._getMD5(key), default={}) or {}
        meta = Globals.settings.getCacheSetting('%s.meta' % key, FileAccess._getMD5('%s.meta' % key), default={}) or {}
        prev = meta.get('prev') if isinstance(meta, dict) else {}
        if prev and master != prev:
            merged = self._mergeMeta(master, dict(user), prev)
            if merged != user:
                Globals.settings.setCacheSetting(key, merged, FileAccess._getMD5(key), life=-1)
                user = merged
            Globals.settings.setCacheSetting('%s.meta' % key, {'prev': master},
                                             FileAccess._getMD5('%s.meta' % key), life=-1)
        return user if user else master

    @staticmethod
    def _mergeMeta(master: Any, user: Any, base: Any) -> Any:
        """Recursive 3-way merge. Where the user's value still equals the previous
        master (base), adopt the new master value; user-customized values are kept;
        new master keys are added."""
        if isinstance(master, dict) and isinstance(user, dict):
            out = dict(user)
            base = base or {}
            for k, v in master.items():
                if k not in out:
                    out[k] = copy.deepcopy(v)
                elif isinstance(v, dict) and isinstance(out.get(k), dict):
                    out[k] = Seasonal._mergeMeta(v, out.get(k), base.get(k))
                elif base.get(k) == out.get(k):
                    out[k] = copy.deepcopy(v)
            return out
        return copy.deepcopy(master) if user == base else user

    def _monthKey(self, month: str) -> str:
        """Normalize a month name to the seasons.json key form (e.g. 'january' -> 'January')."""
        return month.title()

    def addSeason(self, month: str, day: int, entry: Dict[str, Any]) -> bool:
        """Add or replace one day's holiday entry in seasons.json."""
        data = self.getSeasonsData()
        month = self._monthKey(month)
        data.setdefault(month, {})
        data[month][str(day)] = entry
        return self.setSeasonsData(data)

    def delSeason(self, month: str, day: int) -> bool:
        """Remove one day's holiday entry from seasons.json."""
        data = self.getSeasonsData()
        month = self._monthKey(month)
        if data.get(month, {}).pop(str(day), None) is not None:
            return self.setSeasonsData(data)
        return False

    def addHoliday(self, keyword: str, queries: Dict[str, Any]) -> bool:
        """Add or replace one holiday keyword's episode/movie library queries."""
        data = self.getHolidaysData()
        data[keyword] = queries
        return self.setHolidaysData(data)

    def delHoliday(self, keyword: str) -> bool:
        """Remove one holiday keyword's queries from holidays.json."""
        data = self.getHolidaysData()
        if keyword in data:
            data.pop(keyword)
            return self.setHolidaysData(data)
        return False

    def loadSeasons(self, url: Optional[str] = None) -> bool:
        """Load seasons.json from a URL into the user cache setting (defaults to the local HTTP server)."""
        return self._loadJSON(SEASONS_KEY, SEASONFLE, url)

    def loadHolidays(self, url: Optional[str] = None) -> bool:
        """Load holidays.json from a URL into the user cache setting (defaults to the local HTTP server)."""
        return self._loadJSON(HOLIDAYS_KEY, HOLIDAYFLE, url)

    def _loadJSON(self, key: str, fle: str, url: Optional[str] = None) -> bool:
        if url is None:
            url = 'http://%s/%s' % (Globals.properties.getRemoteHost(), fle)
        try:
            resp = requests.get(url, timeout=10)
            if resp.ok:
                return Globals.settings.setCacheSetting(key, resp.json(), FileAccess._getMD5(key), life=-1)
        except Exception as e:
            self.log('_loadJSON, %s failed: %s' % (fle, e), xbmc.LOGDEBUG)
        return False


    def buildSeasonal(self, holiday: Optional[Dict[str, Any]] = None) -> Generator[Dict[str, Any], None, None]:
        """Build seasonal query items for the given holiday."""
        if holiday is None: holiday = self.getHoliday()
        season  = self.getSeason(holiday.get('keyword'))
        for type, params in list(season.items()):
            for param in params:
                item = copy.deepcopy({'episodes':TV_QUERY,'movies':MOVIE_QUERY}[type.lower()])
                item["holiday"] = holiday
                item["sort"].update(param.get("sort"))
                item["filter"].update(param.get("filter"))
                # Kodi JSONRPC rejects filters with empty field/operator/value mixed with and/or compositions.
                # Remove empty rule keys when composition keys are present.
                if item["filter"].get("and") or item["filter"].get("or"):
                    item["filter"].pop("field", None)
                    item["filter"].pop("operator", None)
                    item["filter"].pop("value", None)
                self.log('buildSeasonal, %s - item = %s'%(holiday.get('name'),item))
                yield item