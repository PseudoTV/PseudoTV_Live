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

SEASONS  = {'January'  :{1: {'name':'New Years Anthologies'                     ,'tagline':''                                            ,'keyword':'newyear' ,'types':['movie','tvshow'],'method':{"tvshow":"random" ,"movie":"random"},"operator":"contains",'fields':['title']                            , 'logo':''},
                         2: {'name':'Science Fiction Week'                      ,'tagline':''                                            ,'keyword':'scifiday','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['genre']                            , 'logo':''},
                         3: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         4: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         5: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''}},
                         
            'February' :{1: {'name':'G.I. Joe Week'                             ,'tagline':'A Real American Hero!'                       ,'keyword':'gijoe'   ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         2: {'name':'Valentines Week'                           ,'tagline':'Love is in the air!'                         ,'keyword':'romance' ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         3: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         4: {'name':'Pokémon Week'                              ,'tagline':'Gotta Catch ''Em All'                        ,'keyword':'pokemon' ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''}},
                        
            'March'    :{1: {'name':'Dr. Seuss Week'                            ,'tagline':'“Think and wonder. Wonder and think.”'       ,'keyword':'seuss'   ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         2: {'name':'Alfred Hitchcock'                          ,'tagline':'“Always make the audience suffer...”'        ,'keyword':'hitch'   ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         3: {'name':' '                                         ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         4: {'name':'J.R.R. Tolkien Week'                       ,'tagline':'One ring to rule them all.'                  ,'keyword':'lotr'    ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         5: {'name':'Quentin Tarantino Week'                    ,'tagline':''                                            ,'keyword':'pulp'    ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['director','writer','plot']         , 'logo':''}},
            
            'April'    :{1: {'name':'Star Trek Week'                            ,'tagline':'To Boldly Go...'                             ,'keyword':'startrek','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         2: {'name':'Anime Week'                                ,'tagline':''                                            ,'keyword':'anime'   ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         3: {'name':'Shakespeare Week'                          ,'tagline':'Non Sans Droict'                             ,'keyword':'othello' ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         4: {'name':'Alien Week'                                ,'tagline':'In space, no one can hear you scream.'       ,'keyword':'aliens'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title']                            , 'logo':''},
                         5: {'name':'Superhero Week'                            ,'tagline':''                                            ,'keyword':'super'   ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre','studio']    , 'logo':''}},
                        
            'May'      :{1: {'name':'Star Wars Week'                            ,'tagline':'May the force be with you.'                  ,'keyword':'starwars','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         2: {'name':'Twilight Zone Week'                        ,'tagline':''                                            ,'keyword':'zone'    ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         3: {'name':'Sherlock Holmes Week'                      ,'tagline':'The Game is Afoot!'                          ,'keyword':'watson'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         4: {'name':'Dracula Week'                              ,'tagline':'Fidelis et mortem'                           ,'keyword':'vampire' ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         5: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''}},
                        
            'June'     :{1: {'name':'Ghostbusters Week'                         ,'tagline':'Who You Gonna Call?'                         ,'keyword':'ghosts'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         2: {'name':'Superman Week'                             ,'tagline':'Truth, justice, and the American way.'       ,'keyword':'superman','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         3: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         4: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         5: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''}},
                        
            'July'     :{1: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         2: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         3: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         4: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         5: {'name':'Harry Potter Week'                         ,'tagline':'Draco Dormiens Nunquam Titillandus'          ,'keyword':'potter'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''}},
                        
            'August'   :{1: {'name':'Spider-Man Week'                           ,'tagline':'with great power comes great responsibility.','keyword':'spider'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         2: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         3: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         4: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         5: {'name':'Power Rangers Week'                        ,'tagline':'“Everyone gets to be a Ranger!”'             ,'keyword':'ranger'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot']                     , 'logo':''}},
                        
            'September':{1: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         2: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         3: {'name':'Batman Week'                               ,'tagline':'The Dark Knight'                             ,'keyword':'batman'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         4: {'name':'Hobbit Week'                               ,'tagline':'out of the frying-pan into the fire.'        ,'keyword':'hobbit'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},                  
                         5: {'name':'Comic Book Week'                           ,'tagline':''                                            ,'keyword':'comic'   ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot','studio']            , 'logo':''}},
                        
            'October'  :{1: {'name':'Back to the Future Week'                   ,'tagline':'Great Scott!'                                ,'keyword':'future'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         2: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         3: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         4: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         5: {'name':'Halloween Season'                          ,'tagline':'Spooky Suggestions'                          ,'keyword':'horror'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''}},
                        
            'November' :{1: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         2: {'name':'Veterans Week'                             ,'tagline':'Honoring all who served'                     ,'keyword':'veterans','types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         3: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         4: {'name':'Doctor Who Week'                           ,'tagline':'Run!'                                        ,'keyword':'tardis'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"year"}  ,"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         5: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''}},
                        
            'December' :{1: {'name':'Disney Week'                               ,'tagline':'Where Dreams Come True'                      ,'keyword':'disney'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','studio']            , 'logo':''},
                         2: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','genre']             , 'logo':''},
                         3: {'name':'Marvel Week'                               ,'tagline':'“Excelsior!”'                                ,'keyword':'marvel'  ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot','studio']            , 'logo':''},
                         4: {'name':''                                          ,'tagline':''                                            ,'keyword':''        ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot']                     , 'logo':''},
                         5: {'name':'Christmas Season'                          ,'tagline':"'Tis the season"                             ,'keyword':'xmas'    ,'types':['movie','tvshow'],'method':{"tvshow":"episode","movie":"random"},"operator":"contains",'fields':['title','plot']                     , 'logo':''}}}
                          
               
KEYWORDS = {'newyear'  :['The Twilight Zone','Black-Mirror','Black Mirror','Outer Limits','Amazing Stories','Tales from the Darkside','Tales from the crypt',
                         'Creepshow','The Hitchhiker','Into the Dark','The Ray Bradbury Theater','American Horror Stories','Anthology'],
            'scifiday' :['Science-Fiction','Science Fiction','Sci-Fi'],
            'gijoe'    :['G.I. Joe','GI Joe'],
            'romance'  :['Valentine','Valentines','Valentine''s Day','Romance','Romcom','Love','Cupid'],
            'pokemon'  :['Pokémon','Pokemon'],
            'seuss'    :['Dr. Seuss','Dr Seuss','Lorox','Horton','Grinch'],
            'hitch'    :['Alfred Hitchcock'],
            'lotr'     :['Hobbit','Lord of the rings','LOTR','Tolkien'],
            'pulp'     :["Quentin Tarantino","Tarantino"],
            'startrek' :['Star Trek'],
            'aliens'   :['Alien','Aliens'],
            'super'    :['Superhero','DC','Marvel','Batman','Superman','Spiderman','Spider-Man','Wonder woman'],
            'starwars' :['Star Wars','Krieg der Sterne','Skywalker','Darth Vader','Jedi ','Ewoks','Boba Fett','Mandalorian' 
                         'Starwars','Yoda ','Obi-Wan','Kenobi','Millennium Falcon','Millenium Falke','Stormtrooper','Sturmtruppler', 'Sith'],
            'zone'     :['The Twilight Zone','Twilight Zone'],
            'watson'   :['Sherlock','Holmes','Watson','Sher-lock'],
            'vampire'  :['Dracula','Vampire','Nosferatu','Vamp','Bloodsucker','Succubus'],
            'ghosts'   :['Ghostbusters'],
            'superman' :['Superman','Krypton','Lex Luther','Louis & Clark','Clark Kent','Man of Steel'],
            'potter'   :['Harry Potter','Fantastic Beasts'],
            'spider'   :['Spider-Man','Spiderman','Peter Parker'],
            'ranger'   :['Power Rangers'],
            'batman'   :['Batman','Joker','Dark Knight'],
            'hobbit'   :['Hobbit'],
            'comic'    :['DC','Marvel','Batman','Superman','Spiderman','Spider-Man','Wonder woman'],
            'future'   :['Back to the Future'],
            'horror'   :['ужас','užas','rædsel','horror','φρίκη','õudus','kauhu','horreur','užas',
                         'borzalom','hryllingi','ホラー','siaubas','verschrikking','skrekk','przerażenie',
                         'groază','фильм ужасов','hrôza','grozo','Skräck','korku','жах','halloween'],
            'veterans' :['World War One','World War Two','V-Day','D-Day','WWI','WWII','Pearl Harbor','Dunkirk','War','World War',
                         'Vietnam','Warfare','Army','Navy','Naval','Marine','Air Force','Military','Soldier','Cadet','Officer','Korean War'],
            'tardis'   :['Tardis','Doctor Who','Dr. Who','Dr Who'],
            'disney'   :['Pixar','Disney','Mickey Mouse'],
            'marvel'   :['Marvel','Spiderman','Spider-Man','X-Men','Deadpool','The Avengers'],
            'xmas'     :['xmas','christmas','x-mas','santa claus','st. claus','happy holidays','st. nick','Weihnacht',
                         'fest der liebe','heilige nacht','heiliger abend','heiligabend','nikolaus','christkind','Noël',
                         'Meilleurs vœux','feliz navidad','joyeux noel','Natale','szczęśliwe święta','Veselé Vánoce',
                         'Vrolijk kerstfeest','Kerstmis','Boże Narodzenie','Kalėdos','Crăciun']}
                                                
EXCLUDE  = [{"field":"season" ,"operator":"greaterthan","value":"0"},
            {"field":"episode","operator":"greaterthan","value":"0"}]
    
class Seasonal:
    def __init__(self, builder=None):
        if builder is None: return
        self.builder = builder
        self.writer  = builder.writer
        self.cache   = builder.cache
        
                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getWeek(self):
        dt = datetime.datetime.now()
        adjusted_dom = dt.day + dt.replace(day=1).weekday()
        return int(ceil(adjusted_dom/7.0))


    def getMonth(self):
        return datetime.datetime.now().strftime('%B')


    def getCurrentHoliday(self):
        return SEASONS.get(self.getMonth(),{}).get(self.getWeek(),{})


    def getNearestHoliday(self):
        holiday = {}
        month   = self.getMonth()
        week    = self.getWeek()
        weeks   = [1,2,3,4,5][week-1:] #running a 5 week month for extended weeks > 28 days.
        for next in weeks:
            holiday = SEASONS.get(month,{}).get(next,{})
            if holiday.get('keyword'): break
        self.log('getNearestHoliday, month = %s, week = %s, found = %s'%(month, week, holiday))
        return holiday


    def buildPath(self, citem, nearest=SETTINGS.getSettingBool('NEAREST_SEASON')):
        urls = []        
        if nearest: season = self.getNearestHoliday()
        else:       season = self.getCurrentHoliday()
        
        keyword = season.get('keyword','')
        citem['holiday'] = '%s%s'%(season.get('name',''),(' - %s'%(season.get('tagline')) if season.get('tagline','') else ''))
        citem['logo']    = (season.get('logo','') or citem['logo'])
        
        if len(KEYWORDS.get(keyword,[])) > 0:
            for type in season.get('types',[]):
                sort     = {"tvshow":"episodes","movie":"movies"}[type]
                method   = season.get('method',{"tvshow":"episode","movie":"random"})[type]
                operator = season.get('operator','contains')
                for field in season.get('fields',[]):
                    if field == 'title' and type == 'tvshow': field = 'tvshow'
                    payload = {"order":{"direction":"ascending","ignorefolders":0,"method":method},"rules":{"and":[{"field":field,"operator":operator,"value":KEYWORDS.get(keyword,[])}]},"type":sort}
                    if   type == 'tvshow': urls.append(TV_URL%(dumpJSON(payload)))
                    elif type == 'movie':  urls.append(MOVIE_URL%(dumpJSON(payload)))
                    
        self.log('buildPath, returning urls = %s'%(urls))
        return citem, urls