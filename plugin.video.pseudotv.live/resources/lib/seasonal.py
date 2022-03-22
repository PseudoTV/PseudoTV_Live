#   Copyright (C) 2022 Lunatixz
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

from resources.lib.globals     import *

# https://www.holidaysmart.com/holidays/daily/fandom
# https://www.holidaysmart.com/holidays/daily/tv-movies

MOVIE_URL= 'videodb://movies/titles/?xsp=%s'
TV_URL   = 'videodb://tvshows/titles/-1/-1/-1/-1/?xsp=%s'

SEASONS  = {'January'  :{1: {'name':'New Years Anthologies'                     ,'keyword':'newyear' ,'types':['movie','tvshow'],'method':{"tvshow":"random" ,"movie":"random"},"operator":"contains",'fields':['title','originaltitle','genre']        , 'logo':''},
                         2: {'name':'New Years Anthologies'                     ,'keyword':'newyear' ,'types':['movie','tvshow'],'method':{"tvshow":"random" ,"movie":"random"},"operator":"contains",'fields':['title','originaltitle','genre']        , 'logo':''},
                         3: {'name':'Science Fiction Week'                      ,'keyword':'scifiday','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['genre']                                , 'logo':''},
                         4: {'name':'Science Fiction Week'                      ,'keyword':'scifiday','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['genre']                                , 'logo':''}},
                         
            'February' :{1: {'name':'G.I. Joe Week'                             ,'keyword':'gijoe'   ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         2: {'name':'Love is in the air (Valentines Week)'      ,'keyword':'romance' ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         3: {'name':'Love is in the air (Valentines Week)'      ,'keyword':'romance' ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         4: {'name':'Pokémon Week'                              ,'keyword':'pokemon' ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''}},
                        
            'March'    :{1: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         2: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         3: {'name':' '                                         ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         4: {'name':'J.R.R. Tolkien Week'                       ,'keyword':'lotr'    ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''}},
            
            'April'    :{1: {'name':'Live long and prosper (Star Trek Week)'    ,'keyword':'startrek','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         2: {'name':'Live long and prosper (Star Trek Week)'    ,'keyword':'startrek','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         3: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         4: {'name':'Alien Week'                                ,'keyword':'aliens'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle']                , 'logo':''}},
                        
            'May'      :{1: {'name':'May the force be with you (Star Wars Week)','keyword':'starwars','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         2: {'name':'May the force be with you (Star Wars Week)','keyword':'starwars','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         3: {'name':'Sherlock Holmes Week'                      ,'keyword':'watson'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         4: {'name':'Dracula Week'                              ,'keyword':'vampire' ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''}},
                        
            'June'     :{1: {'name':'Ghostbusters Week'                         ,'keyword':'ghosts'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         2: {'name':'Superman Week'                             ,'keyword':'superman','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         3: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         4: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''}},
                        
            'July'     :{1: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         2: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         3: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         4: {'name':'Harry Potter Week'                         ,'keyword':'potter'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''}},
                        
            'August'   :{1: {'name':'Spiderman Week'                            ,'keyword':'spider'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         2: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         3: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         4: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''}},
                        
            'September':{1: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         2: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         3: {'name':'Batman Week'                               ,'keyword':'batman'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         4: {'name':'Comic Book Week'                           ,'keyword':'comic'   ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot','studio'], 'logo':''}},
                        
            'October'  :{1: {'name':'Back to the Future Week'                   ,'keyword':'future'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         2: {'name':'Spooky Suggestions (Halloween)'            ,'keyword':'horror'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         3: {'name':'Spooky Suggestions (Halloween)'            ,'keyword':'horror'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         4: {'name':'Spooky Suggestions (Halloween)'            ,'keyword':'horror'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''}},
                        
            'November' :{1: {'name':'Honoring all who served (Veterans Week)'   ,'keyword':'veterans','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         2: {'name':'Honoring all who served (Veterans Week)'   ,'keyword':'veterans','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','genre'] , 'logo':''},
                         3: {'name':''                                          ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         4: {'name':'Doctor Who Week'                           ,'keyword':'tardis'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''}},
                        
            'December' :{1: {'name':'Disney Week'                               ,'keyword':'disney'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot','studio'], 'logo':''},
                         2: {'name':'Christmas Holiday Season'                  ,'keyword':'xmas'    ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         3: {'name':'Christmas Holiday Season'                  ,'keyword':'xmas'    ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''},
                         4: {'name':'Christmas Holiday Season'                  ,'keyword':'xmas'    ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','originaltitle','plot']         , 'logo':''}}}
                          
               
KEYWORDS = {'newyear'  :['The Twilight Zone','Black-Mirror','Black Mirror','Outer Limits','Amazing Stories','Tales from the Darkside','Tales from the crypt',
                         'Creepshow','The Hitchhiker','Into the Dark','The Ray Bradbury Theater','American Horror Stories','Anthology'],
            'scifiday' :['Science-Fiction','Science Fiction','Sci-Fi'],
            'gijoe'    :['G.I. Joe','GI Joe'],
            'romance'  :['Valentine','Valentines','Valentine''s Day','Romance','Romcom','Love','Cupid'],
            'pokemon'  :['Pokémon','Pokemon'],
            'lotr'     :['Hobbit','Lord of the rings','LOTR','Tolkien'],
            'startrek' :['Star Trek', 'Captain Kirk', 'Cpt. Kirk', 'James Kirk', 'James T. Kirk', 'James Tiberius Kirk',
                         'Jean-Luc Picard', 'Commander Spock', 'Deep Space Nine', 'Deep Space 9', 'Raumschiff Enterprise',
                         'Raumschiff Voyager', 'Klingonen', 'Klingons', 'Commander Data', 'Commander Geordi La Forge',
                         'Counselor Deanna Troi', 'William Thomas Riker', 'Captain Benjamin Sisko', 'Cpt. Benjamin Sisko',
                         'Captain Kathryn Janeway', 'Cpt. Kathryn Janeway'],
            'aliens'   :['Alien','Aliens'],
            'starwars' :['Star Wars', 'Krieg der Sterne', 'Skywalker', 'Darth Vader', 'Jedi ', 'Ewoks', 'Boba Fett', 'Mandalorian' 
                         'Starwars', 'Kylo Ren', 'Yoda ', 'Chewbacca', 'Han Solo', 'r2-d2', 'Obi-Wan', 'Kenobi',
                         'bb-8', 'Millennium Falcon', 'Millenium Falke', 'Stormtrooper', 'Sturmtruppler', 'Sith'],
            'watson'   :['Sherlock','Holmes','Watson'],
            'vampire'  :['Dracula','Vampire','Nosferatu','Vamp','Bloodsucker','Succubus'],
            'ghosts'   :['Ghostbusters'],
            'superman' :['Superman','Krypton','Lex Luther','Louis & Clark','Clark Kent','Man of Steel'],
            'potter'   :['Harry Potter','Fantastic Beasts'],
            'spider'   :['Spider-Man','Spiderman','Peter Parker'],
            'batman'   :['Batman','Joker','Dark Knight'],
            'comic'    :['DC','Marvel'],
            'future'   :['Back to the Future'],
            'horror'   :['ужас', 'užas', 'rædsel', 'horror', 'φρίκη', 'õudus', 'kauhu', 'horreur', 'užas',
                         'borzalom', 'hryllingi', 'ホラー', 'siaubas', 'verschrikking', 'skrekk', 'przerażenie',
                         'groază', 'фильм ужасов', 'hrôza', 'grozo', 'Skräck', 'korku', 'жах', 'halloween'],
            'veterans' :['World War One', 'World War Two', 'V-Day', 'D-Day', 'WWI', 'WWII', 'Pearl Harbor', 'Dunkirk', 'War', 'Vietnam', 'Warfare', 'Army', 'Navy', 'Naval', 'Marine', 'Air Force', 'Military'],
            'tardis'   :['Tardis','Doctor Who','Dr. Who','Dr Who'],
            'disney'   :['Pixar','Disney','Mickey Mouse'],
            'xmas'     :['xmas', 'christmas', 'x-mas', 'santa claus', 'st. claus', 'happy holidays', 'st. nick', 'Weihnacht',
                         'fest der liebe', 'heilige nacht', 'heiliger abend', 'heiligabend', 'nikolaus', 'christkind', 'Noël',
                         'Meilleurs vœux', 'feliz navidad', 'joyeux noel', 'Natale', 'szczęśliwe święta', 'Veselé Vánoce',
                         'Vrolijk kerstfeest', 'Kerstmis', 'Boże Narodzenie', 'Kalėdos', 'Crăciun']}
                                                
EXCLUDE  = [{"field":"season" ,"operator":"greaterthan","value":"0"},
            {"field":"episode","operator":"greaterthan","value":"0"}]
    
class Seasonal:
    def __init__(self, builder=None):
        if builder is None: return
        self.builder = builder
        self.writer  = builder.writer
        self.cache   = builder.cache
        self.pool    = builder.pool
        
                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getWeek(self):
        dt = datetime.datetime.now()
        adjusted_dom = dt.day + dt.replace(day=1).weekday()
        return int(ceil(adjusted_dom/7.0))


    def getMonth(self):
        return datetime.datetime.now().strftime('%B')


    def getNearestHoliday(self):
        holiday = {}
        month   = self.getMonth()
        week    = self.getWeek()
        weeks   = [1,2,3,4][week-1:]
        for next in weeks:
            holiday = SEASONS.get(month,{}).get(next,{})
            if holiday.get('keyword'): break
        self.log('getNearestHoliday, month = %s, week = %s, found = %s'%(month, week, holiday))
        return holiday


    def buildPath(self, citem):
        url     = []
        filters = []
        season  = self.getNearestHoliday()
        keyword = season.get('keyword','')
        citem['holiday'] = season.get('name','')
        citem['logo']    = (season.get('logo','') or citem['logo'])
        
        if len(KEYWORDS.get(keyword,[])) > 0:
            for type in season.get('types',[]):
                for field in season.get('fields',[]):
                    filters.append({"field":"%s"%(field),"operator":"%s"%(season.get('operator','contains')),"value":KEYWORDS.get(keyword,[])})
                
                if len(filters) > 0:
                    sort    = {"tvshow":"episodes","movie":"movies"}[type]
                    method  = season.get('method',{"tvshow":"episode","movie":"random"})[type]
                    payload = {"order":{"direction":"ascending","ignorefolders":0,"method":"%s"%(method)},"rules":{"or":filters},"type":"%s"%(sort)}
                    if   type == 'tvshow': url.append(TV_URL%(dumpJSON(payload)))
                    elif type == 'movie':  url.append(MOVIE_URL%(dumpJSON(payload)))
                        
        self.log('buildPath, returning url = %s'%(url))
        return citem, url