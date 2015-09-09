import datetime
from Utils import *
from local_db import compare_with_library

TRAKT_KEY = 'e9a7fba3fa1b527c08c073770869c258804124c5d7c984ce77206e695fbaddd5'
BASE_URL = "https://api-v2launch.trakt.tv/"
HEADERS = {
    'Content-Type': 'application/json',
    'trakt-api-key': TRAKT_KEY,
    'trakt-api-version': 2
}


def GetTraktCalendarShows(Type):
    shows = []
    url = ""
    if Type == "shows":
        url = 'calendars/shows/%s/14?extended=full,images' % datetime.date.today()
    elif Type == "premieres":
        url = 'calendars/shows/premieres/%s/14?extended=full,images' % datetime.date.today()
    try:
        results = Get_JSON_response(BASE_URL + url, 0.5, headers=HEADERS)
    except:
        log("Error when fetching Trakt data from net")
        log("Json Query: " + url)
        results = None
    count = 1
    if results is not None:
        for day in results.iteritems():
            for episode in day[1]:
                banner = episode["show"]["images"]["banner"]["full"]
                fanart = episode["show"]["images"]["fanart"]["full"]
                poster = episode["show"]["images"]["poster"]["full"]
                show = {'Title': episode["episode"]["title"],
                        'TVShowTitle': episode["show"]["title"],
                        'tvdb_id': episode["show"]["ids"]["tvdb"],
                        'Runtime': episode["show"]["runtime"],
                        'duration': episode["show"]["runtime"],
                        'duration(h)': format_time(episode["show"]["runtime"], "h"),
                        'duration(m)': format_time(episode["show"]["runtime"], "m"),
                        'Year': fetch(episode["show"], "year"),
                        'Certification': episode["show"]["certification"],
                        'Studio': episode["show"]["network"],
                        'Plot': episode["show"]["overview"],
                        'Genre': " / ".join(episode["show"]["genres"]),
                        'Thumb': episode["episode"]["images"]["screenshot"]["thumb"],
                        'Art(poster)': poster,
                        'Poster': poster,
                        'Art(banner)': banner,
                        'Banner': banner,
                        'Art(fanart)': fanart,
                        'Fanart': fanart}
                shows.append(show)
                count += 1
                if count > 20:
                    break
    return shows


def HandleTraktMovieResult(results):
    movies = []
    for movie in results:
        if ADDON.getSetting("infodialog_onclick") != "false":
            path = 'plugin://script.extendedinfo/?info=action&&id=RunScript(script.extendedinfo,info=extendedinfo,id=%s)' % str(fetch(movie["movie"]["ids"], 'tmdb'))
        else:
            path = "plugin://script.extendedinfo/?info=playtrailer&&id=" + str(fetch(movie["movie"]["ids"], 'tmdb'))
        movie = {'Title': movie["movie"]["title"],
                 'Runtime': movie["movie"]["runtime"],
                 'duration': movie["movie"]["runtime"],
                 'duration(h)': format_time(movie["movie"]["runtime"], "h"),
                 'duration(m)': format_time(movie["movie"]["runtime"], "m"),
                 'Tagline': movie["movie"]["tagline"],
                 'Trailer': ConvertYoutubeURL(movie["movie"]["trailer"]),
                 'Year': movie["movie"]["year"],
                 'ID': movie["movie"]["ids"]["tmdb"],
                 'imdb_id': movie["movie"]["ids"]["imdb"],
                 'Path': path,
                 'mpaa': movie["movie"]["certification"],
                 'Plot': movie["movie"]["overview"],
                 'Premiered': movie["movie"]["released"],
                 'Rating': round(movie["movie"]["rating"], 1),
                 'Votes': movie["movie"]["votes"],
                 'Watchers': movie["watchers"],
                 'Genre': " / ".join(movie["movie"]["genres"]),
                 'Art(poster)': movie["movie"]["images"]["poster"]["full"],
                 'Poster': movie["movie"]["images"]["poster"]["full"],
                 'Art(fanart)': movie["movie"]["images"]["fanart"]["full"],
                 'Fanart': movie["movie"]["images"]["fanart"]["full"]}
        movies.append(movie)
    movies = compare_with_library(movies, False)
    return movies


def HandleTraktTVShowResult(results):
    shows = []
    for tvshow in results:
        airs = fetch(tvshow['show'], "airs")
        path = 'plugin://script.extendedinfo/?info=action&&id=RunScript(script.extendedinfo,info=extendedtvinfo,imdb_id=%s)' % tvshow['show']['ids']["imdb"]
        show = {'Title': tvshow['show']["title"],
                'Label': tvshow['show']["title"],
                'TVShowTitle': tvshow['show']["title"],
                'Runtime': tvshow['show']["runtime"],
                'duration': tvshow['show']["runtime"],
                'duration(h)': format_time(tvshow['show']["runtime"], "h"),
                'duration(m)': format_time(tvshow['show']["runtime"], "m"),
                'Year': tvshow['show']["year"],
                'Status': fetch(tvshow['show'], "status"),
                'mpaa': tvshow['show']["certification"],
                'Studio': tvshow['show']["network"],
                'Plot': tvshow['show']["overview"],
                'tvdb_id': tvshow['show']['ids']["tvdb"],
                'imdb_id': tvshow['show']['ids']["imdb"],
                'Path': path,
                'AirDay': fetch(airs, "day"),
                'AirShortTime': fetch(airs, "time"),
                'Label2': fetch(airs, "day") + " " + fetch(airs, "time"),
                'Premiered': tvshow['show']["first_aired"][:10],
                'Country': tvshow['show']["country"],
                'Rating': round(tvshow['show']["rating"], 1),
                'Votes': tvshow['show']["votes"],
                'Watchers': fetch(tvshow, "watchers"),
                'Genre': " / ".join(tvshow['show']["genres"]),
                'Art(poster)': tvshow['show']["images"]["poster"]["full"],
                'Poster': tvshow['show']["images"]["poster"]["full"],
                'Art(banner)': tvshow['show']["images"]["banner"]["full"],
                'Banner': tvshow['show']["images"]["banner"]["full"],
                'Art(fanart)': tvshow['show']["images"]["fanart"]["full"],
                'Fanart': tvshow['show']["images"]["fanart"]["full"],
                'Thumb': tvshow['show']["images"]["fanart"]["thumb"]}
        shows.append(show)
    return shows


def GetTrendingShows():
    url = 'shows/trending?extended=full,images'
    results = Get_JSON_response(BASE_URL + url, headers=HEADERS)
    if results is not None:
        return HandleTraktTVShowResult(results)
    else:
        return []


def GetTVShowInfo(imdb_id):
    url = 'show/%s?extended=full,images' % imdb_id
    results = Get_JSON_response(BASE_URL + url, headers=HEADERS)
    if results is not None:
        return HandleTraktTVShowResult([results])
    else:
        return []


def GetTrendingMovies():
    url = 'movies/trending?extended=full,images'
    results = Get_JSON_response(BASE_URL + url, headers=HEADERS)
    if results is not None:
        return HandleTraktMovieResult(results)
    else:
        return []


def GetSimilarTrakt(mediatype, imdb_id):
    if imdb_id is not None:
        url = '%s/%s/related?extended=full,images' % (mediatype, imdb_id)
        results = Get_JSON_response(BASE_URL + url, headers=HEADERS)
        if results is not None:
            if mediatype == "show":
                return HandleTraktTVShowResult(results)
            elif mediatype == "movie":
                return HandleTraktMovieResult(results)
    else:
        Notify("Error when fetching info from Trakt.TV")
        return[]
