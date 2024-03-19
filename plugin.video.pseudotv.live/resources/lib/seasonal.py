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
#adapted from https://github.com/sualfred/script.embuary.helper/blob/matrix

from globals     import *
from seasons     import *

# https://www.holidaysmart.com/holidays/daily/fandom
# https://www.holidaysmart.com/holidays/daily/tv-movies

FILTER      = {"field":"","operator":"","value":[]}
SORT        = {"method":"","order":"","ignorearticle":True,"useartistsortname":True}
KEY_QUERY   = {"method":"","order":"","field":'',"operator":'',"value":[]}

TV_QUERY    = {"path":"videodb://tvshows/titles/" ,"limit":"","sort":{},"filter":{},
               "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"}
               
MOVIE_QUERY = {"path":"videodb://movies/titles/"  ,"limit":"","sort":{},"filter":{},
               "method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie"  ,"key":"movies"}
               
SEASONS     = {"January"   : {'1':{'name':"New Years Anthologies"   , 'tagline':"“You're traveling through another dimension...“"                 , 'keyword':'newyear' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://cdn-icons-png.flaticon.com/512/3763/3763123.png'},
                              '2':{'name':"Science Fiction Week"    , 'tagline':"“Science fiction frees you to go anyplace and examine anything.“", 'keyword':'scifi'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://www.pngall.com/wp-content/uploads/6/Science-Fiction-PNG-Free-Download.png'},
                              '3':{'name':"J.R.R. Tolkien Week"     , 'tagline':"“One ring to rule them all.“"                                    , 'keyword':'lotr'    , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://www.pngall.com/wp-content/uploads/12/Lord-Of-The-Rings-Logo-PNG-Picture.png'},
                              '4':{'name':'Lego Week'               , 'tagline':"“With a bucket of Lego, you can tell any story.“"                , 'keyword':'lego'    , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://pngimg.com/d/lego_PNG99.png'},
                              '5':{'name':''                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},

               "February"  : {'1':{'name':"G.I. Joe Week"           , 'tagline':"“A Real American Hero!“"                                         , 'keyword':'gijoe'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://preview.redd.it/zul0o3zwo2r71.png?width=640&crop=smart&auto=webp&s=4ad37682d57f808ce82dba51c9aeaebce5b59258'}, 
                              '2':{'name':"Valentines Week"         , 'tagline':"“Love is in the air!“"                                           , 'keyword':'romance' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://icons.iconarchive.com/icons/designbolts/valentine/512/Happy-valentines-day-icon.png'},
                              '3':{'name':"Pokémon Week"            , 'tagline':"“Gotta Catch ""em All“"                                          , 'keyword':'pokemon' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://w7.pngwing.com/pngs/427/428/png-transparent-pokemon-logo-pokemon-go-pikachu-logo-ash-ketchum-pokemon-go-text-banner-sign.png'},
                              '4':{'name':"Superman Week"           , 'tagline':"“Truth, justice, and the American way.“"                         , 'keyword':'superman', 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Superman_S_symbol.svg/2560px-Superman_S_symbol.svg.png'},
                              '5':{'name':''                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                          
               "March"     : {'1':{'name':"Dr. Seuss Week"          , 'tagline':"“Think and wonder. Wonder and think.”"                           , 'keyword':'seuss'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://static.wikia.nocookie.net/logopedia/images/9/90/Dr._Seuss.svg/revision/latest?cb=20180125222130',}, 
                              '2':{'name':"Alfred Hitchcock Week"   , 'tagline':"“Always make the audience suffer...”"                            , 'keyword':'hitch'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://upload.wikimedia.org/wikipedia/fr/6/6b/Alfred_Hitchcock_pr%C3%A9sente.png'},
                              '3':{'name':"St. Patrick's Week"      , 'tagline':"“May the luck of the Irish lead to happiest heights...”"         , 'keyword':'patrick' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://seeklogo.com/images/H/happy-st-patricks-day-logo-AFF883C309-seeklogo.com.png'},
                              '4':{'name':"J.R.R. Tolkien Week"     , 'tagline':"“One ring to rule them all.“"                                    , 'keyword':'lotr'    , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://www.pngall.com/wp-content/uploads/12/Lord-Of-The-Rings-Logo-PNG-Picture.png'},
                              '5':{'name':"Quentin Tarantino Week"  , 'tagline':"“If you just love movies enough, you can make a good one.”"      , 'keyword':'quentin' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://rat.in.ua/wp-content/uploads/2019/11/4758-Written-and-Directed-by-Quentin-Tarantino.png'}},
                          
               "April"     : {'1':{'name':"Star Trek Week"          , 'tagline':"“To Boldly Go...“"                                               , 'keyword':'startrek', 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Star_Trek_TOS_logo.svg/2560px-Star_Trek_TOS_logo.svg.png'}, 
                              '2':{'name':"Shakespeare Week"        , 'tagline':"“Non Sans Droict“"                                               , 'keyword':'othello' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '3':{'name':"Superhero Week"          , 'tagline':"“I Can Do This All Day!“"                                        , 'keyword':'super'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '4':{'name':"Alien Week"              , 'tagline':"“In space, no one can hear you scream.“"                         , 'keyword':'aliens'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '5':{'name':"Star Wars Week"          , 'tagline':"“May the force be with you.“"                                    , 'keyword':'starwars', 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                              
               "May"       : {'1':{'name':"Star Wars Week"          , 'tagline':"“May the force be with you.“"                                    , 'keyword':'starwars', 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '2':{'name':"Twilight Zone Week"      , 'tagline':"“You are about to enter another dimension...“"                   , 'keyword':'twilight', 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '3':{'name':"Sherlock Holmes Week"    , 'tagline':"“The Game is Afoot!“"                                            , 'keyword':'watson'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '4':{'name':"Dracula Week"            , 'tagline':"“Fidelis et mortem“"                                             , 'keyword':'vampire' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '5':{'name':""                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                              
               "June"      : {'1':{'name':""                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '2':{'name':"Ghostbusters Week"       , 'tagline':"“Who You Gonna Call?“"                                           , 'keyword':'ghosts'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '3':{'name':"Superman Week"           , 'tagline':"“Truth, justice, and the American way.“"                         , 'keyword':'superman', 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Superman_S_symbol.svg/2560px-Superman_S_symbol.svg.png'},
                              '4':{'name':''                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '5':{'name':''                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                              
               "July"      : {'1':{'name':''                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '2':{'name':''                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '3':{'name':"Disney Week"             , 'tagline':"“Where Dreams Come True.“"                                       , 'keyword':'disney'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '4':{'name':"Harry Potter Week"       , 'tagline':"“Draco Dormiens Nunquam Titillandus“"                            , 'keyword':'potter'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '5':{'name':"Harry Potter Week"       , 'tagline':"“Draco Dormiens Nunquam Titillandus“"                            , 'keyword':'potter'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                              
               "August"    : {'1':{'name':"Spiderman Week"          , 'tagline':"“with great power comes great responsibility“"                   , 'keyword':'spider'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '2':{'name':""                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '3':{'name':"SpongeBob Week"          , 'tagline':"“Three hours later“"                                             , 'keyword':'sponge'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '4':{'name':"Power Rangers Week"      , 'tagline':"“Everyone gets to be a Ranger!”"                                 , 'keyword':'ranger'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '5':{'name':''                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                              
               "September" : {'1':{'name':"Star Trek Week"          , 'tagline':"“To Boldly Go...“"                                               , 'keyword':'startrek', 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Star_Trek_TOS_logo.svg/2560px-Star_Trek_TOS_logo.svg.png'},
                              '2':{'name':"Batman Week"             , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '3':{'name':"Hobbit Week"             , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '4':{'name':"Comic Book Week"         , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '5':{'name':"Comic Book Week"         , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                              
               "October"   : {'1':{'name':"Willy Wonka Week"        , 'tagline':"“The Suspense Is Terrible. I Hope It’ll Last.”"                  , 'keyword':'wonka'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '2':{'name':"Back to the Future Week" , 'tagline':"“Great Scott!”"                                                  , 'keyword':'future'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '3':{'name':""                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '4':{'name':"Halloween Season"        , 'tagline':"Spooky Suggestions"                                              , 'keyword':'horror'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '5':{'name':"Halloween Season"        , 'tagline':"Spooky Suggestions"                                              , 'keyword':'horror'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                              
               "November"  : {'1':{'name':""                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '2':{'name':"Veterans Week"           , 'tagline':"“Honoring all who served”"                                       , 'keyword':'heros'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '3':{'name':"Doctor Who Week"         , 'tagline':"“Run!”"                                                          , 'keyword':'who'     , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '4':{'name':"Thanksgiving Week"       , 'tagline':''                                                                , 'keyword':'turkey'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '5':{'name':"Marvel Week"             , 'tagline':"“Excelsior!”"                                                    , 'keyword':'marvel'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}}, 
                              
               "December"  : {'1':{'name':"Marvel Week"             , 'tagline':"“Excelsior!”"                                                    , 'keyword':'marvel'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '2':{'name':""                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '3':{'name':""                        , 'tagline':''                                                                , 'keyword':''        , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '4':{'name':"Holiday Season"          , 'tagline':"“Tis the season“"                                                , 'keyword':'xmas'    , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                              '5':{'name':"New Years Anthologies"   , 'tagline':"“You're traveling through another dimension...“"                 , 'keyword':'newyear' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://cdn-icons-png.flaticon.com/512/3763/3763123.png'}}}

class Seasonal:
    def __init__(self):
        self.log('__init__')


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getMonth(self):
        return datetime.datetime.now().strftime('%B')


    def getWeek(self):
        dt = datetime.datetime.now()
        adjusted_dom = dt.day + dt.replace(day=1).weekday()
        week = (adjusted_dom/7.0)
        if week > 4.0: return int(ceil(week))
        else:          return int(floor(week))


    def getCurrentHoliday(self):
        return SEASONS.get(self.getMonth(),{}).get(self.getWeek(),{})
        
        
    def getNearestHoliday(self, fallback=True):
        holiday = {}
        month   = self.getMonth()
        week    = self.getWeek()
        weeks   = [1,2,3,4,5][week-1:] #running a 5 week month for extended weeks > 28 days.
        if fallback:
            past = [1,2,3,4,5][:week-1]
            past.reverse()
            weeks = weeks + past
        for next in weeks:
            holiday = SEASONS.get(month,{}).get(str(next),{})
            if holiday.get('keyword'): break
        self.log('getNearestHoliday, using fallback = %s, month = %s, week = %s, nearest week = %s, returning = %s'%(fallback, month, week, next, holiday))
        return holiday
        
        
    def buildSeasonal(self, nearest=SETTINGS.getSettingBool('NEAREST_SEASON')):
        self.log('buildSeasonal, nearest = %s'%(nearest))
        if nearest: season = self.getNearestHoliday()
        else:       season = self.getCurrentHoliday()
        for query in season.get('query',[]):
            for param in KEYWORDS.get(season.get('keyword',{})).get(query.get('key',{})):
                item = query.copy()
                holiday = season.copy()
                holiday.pop("query")
                item["holiday"] = holiday
                item_sort = SORT.copy()
                item_sort.update(param.pop("sort"))
                item["sort"]   = item_sort
                item["filter"] = param.pop("filter")
                yield item