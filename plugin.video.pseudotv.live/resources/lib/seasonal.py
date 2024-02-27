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
# from seasons     import *

SEASONS  = {"January"  :{1: {"name":"New Years Anthologies"                    ,"tagline":""                                             ,"keyword":"newyear" ,"types":["movie","tvshow"],"method":{"tvshow":"random" ,"movie":"random"},"operator":"contains","fields":["title"]                            , "logo":"https://png.pngtree.com/png-vector/20191027/ourmid/pngtree-happy-new-year-text-png-image_1859009.jpg"},
                         2: {"name":"Science Fiction Week"                     ,"tagline":""                                             ,"keyword":"scifiday","types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["genre"]                            , "logo":"http://static1.squarespace.com/static/552d143de4b09906febc898c/t/553231dee4b047c173d7b2f1/1429352959406/SFword_RGB_Y.png"},
                         3: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         4: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         5: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""}},
                         
            "February" :{1: {"name":"G.I. Joe Week"                            ,"tagline":"A Real American Hero!"                        ,"keyword":"gijoe"   ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://preview.redd.it/dshapurrna281.png"},
                         2: {"name":"Valentines Week"                          ,"tagline":"Love is in the air!"                          ,"keyword":"romance" ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":"https://icons.iconarchive.com/icons/designbolts/valentine/512/Happy-valentines-day-icon.png"},
                         3: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         4: {"name":"Pokémon Week"                             ,"tagline":"“Gotta Catch ""em All“"                       ,"keyword":"pokemon" ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://toppng.com/uploads/preview/pokemon-logo-logo-transparent-png-11661032808rmeh0gnodc.png"}},
                        
            "March"    :{1: {"name":"Dr. Seuss Week"                           ,"tagline":"“Think and wonder. Wonder and think.”"        ,"keyword":"seuss"   ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot"]                     , "logo":"https://betterstudio.com/wp-content/uploads/2022/11/5-dr-seuss-logo-PNG-betterstudio.com_.png"},
                         2: {"name":"Alfred Hitchcock"                         ,"tagline":"“Always make the audience suffer...”"         ,"keyword":"hitch"   ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot"]                     , "logo":""},
                         3: {"name":" "                                        ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":""},
                         4: {"name":"J.R.R. Tolkien Week"                      ,"tagline":"“One ring to rule them all.“"                 ,"keyword":"lotr"    ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":""},
                         5: {"name":"Quentin Tarantino Week"                   ,"tagline":""                                             ,"keyword":"pulp"    ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["director","writer","plot"]         , "logo":""}},
            
            "April"    :{1: {"name":"Star Trek Week"                           ,"tagline":"“To Boldly Go...“"                            ,"keyword":"startrek","types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://www.pngmart.com/files/10/Star-Trek-Logo-Transparent-PNG.png"},
                         2: {"name":"Anime Week"                               ,"tagline":""                                             ,"keyword":"anime"   ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":"https://www.pikpng.com/pngl/m/225-2258809_anime-logo-png-dj-anime-logo-clipart.png"},
                         3: {"name":"Shakespeare Week"                         ,"tagline":"“Non Sans Droict“"                            ,"keyword":"othello" ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":"https://w7.pngwing.com/pngs/756/980/png-transparent-hamlet-shakespeare-s-handwriting-romeo-and-juliet-shakespeare-s-r-j-macbeth-others.png"},
                         4: {"name":"Alien Week"                               ,"tagline":"“In space, no one can hear you scream.“"      ,"keyword":"aliens"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title"]                            , "logo":"https://www.clipartmax.com/png/middle/133-1336219_alien-movie-logo-png.png"},
                         5: {"name":"Superhero Week"                           ,"tagline":"“I Can Do This All Day!“"                     ,"keyword":"super"   ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre","studio"]    , "logo":"https://raisely-images.imgix.net/national-superhero-week/uploads/artboard-4-png-eb2608.png"}},
                        
            "May"      :{1: {"name":"Star Wars Week"                           ,"tagline":"“May the force be with you.“"                 ,"keyword":"starwars","types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://pngimg.com/d/star_wars_logo_PNG28.png"},
                         2: {"name":"Twilight Zone Week"                       ,"tagline":"“You are about to enter another dimension...“","keyword":"zone"    ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":""},
                         3: {"name":"Sherlock Holmes Week"                     ,"tagline":"“The Game is Afoot!“"                         ,"keyword":"watson"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://www.clipartmax.com/png/middle/456-4564142_welcome-to-our-hand-picked-9th-grade-clipart-page-please-imagen-de.png"},
                         4: {"name":"Dracula Week"                             ,"tagline":"“Fidelis et mortem“"                          ,"keyword":"vampire" ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot"]                     , "logo":"https://www.pioneerdrama.com/Images/Title_Art/DRACULA.png"},
                         5: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""}},
                        
            "June"     :{1: {"name":"Ghostbusters Week"                        ,"tagline":"“Who You Gonna Call?“"                        ,"keyword":"ghosts"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://www.freepnglogos.com/uploads/ghostbusters-png-logo/ghostbusters-images-png-logo-7.png"},
                         2: {"name":"Superman Week"                            ,"tagline":"Truth, justice, and the American way."        ,"keyword":"superman","types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://www.freeiconspng.com/uploads/superman-logo-png-20.png"},
                         3: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         4: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         5: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""}},
                        
            "July"     :{1: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         2: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         3: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":""},
                         4: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":""},
                         5: {"name":"Harry Potter Week"                        ,"tagline":"“Draco Dormiens Nunquam Titillandus“"         ,"keyword":"potter"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://i.pinimg.com/originals/a0/56/6d/a0566dac347529a80ff38a51a56e8d56.png"}},
                        
            "August"   :{1: {"name":"Spider-Man Week"                          ,"tagline":"“with great power comes great responsibility“","keyword":"spider"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://logos-world.net/wp-content/uploads/2020/11/Spider-Man-Logo.png"},
                         2: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         3: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         4: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         5: {"name":"Power Rangers Week"                       ,"tagline":"“Everyone gets to be a Ranger!”"              ,"keyword":"ranger"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot"]                     , "logo":"https://static.wikia.nocookie.net/logopedia/images/0/07/Power_rangers_logo.png"}},
                        
            "September":{1: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         2: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         3: {"name":"Batman Week"                              ,"tagline":"The Dark Knight"                              ,"keyword":"batman"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://www.freepnglogos.com/uploads/3d-batman-vector-logo-png-28.png"},
                         4: {"name":"Hobbit Week"                              ,"tagline":"..out of the frying-pan into the fire."       ,"keyword":"hobbit"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://www.liblogo.com/img-logo/th8627tcb2-the-hobbit-logo-the-hobbit-lego-dimensions-2-the-rise-of-enoch-wiki-.png"},
                         5: {"name":"Comic Book Week"                          ,"tagline":""                                             ,"keyword":"comic"   ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot","studio"]            , "logo":"https://img1.pnghut.com/23/18/1/4pGq0T4FiA/brand-batman-sticker-point-cartoon.jpg"}},
                        
            "October"  :{1: {"name":"Back to the Future Week"                  ,"tagline":"Great Scott!"                                 ,"keyword":"future"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://www.pngarts.com/files/1/Back-To-The-Future-PNG-Image.png"},
                         2: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         3: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         4: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         5: {"name":"Halloween Season"                         ,"tagline":"Spooky Suggestions"                           ,"keyword":"horror"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":"https://www.chandleraz.gov/sites/default/files/styles/social_share/public/cs-halloween-spooktacular-logo-header.png"}},
                        
            "November" :{1: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         2: {"name":"Veterans Week"                            ,"tagline":"Honoring all who served"                      ,"keyword":"veterans","types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":"https://www.pngall.com/wp-content/uploads/2/Veterans-Day-PNG-Clipart.png"},
                         3: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":""},
                         4: {"name":"Doctor Who Week"                          ,"tagline":"Run!"                                         ,"keyword":"tardis"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"year"}  ,"operator":"contains","fields":["title","plot"]                     , "logo":"https://assets.stickpng.com/images/5847f1dccef1014c0b5e485f.png"},
                         5: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""}},
                        
            "December" :{1: {"name":"Disney Week"                              ,"tagline":"Where Dreams Come True"                       ,"keyword":"disney"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","studio"]            , "logo":"https://i.pinimg.com/originals/90/38/a4/9038a431f8f2064eff5abcf4f25d9870.png"},
                         2: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","genre"]             , "logo":""},
                         3: {"name":"Marvel Week"                              ,"tagline":"“Excelsior!”"                                 ,"keyword":"marvel"  ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot","studio"]            , "logo":"http://assets.stickpng.com/thumbs/585f9333cb11b227491c3581.png"},
                         4: {"name":""                                         ,"tagline":""                                             ,"keyword":""        ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot"]                     , "logo":""},
                         5: {"name":"Christmas Season"                         ,"tagline":"“Tis the season“"                             ,"keyword":"xmas"    ,"types":["movie","tvshow"],"method":{"tvshow":"episode","movie":"random"},"operator":"contains","fields":["title","plot"]                     , "logo":"https://www.pngfind.com/pngs/m/185-1856026_merry-christmas-wishes-png-transparent-png.png"}}}
                          
KEYWORDS = {"newyear"  :["The Twilight Zone","Black-Mirror","Black Mirror","Outer Limits","Amazing Stories","Tales from the Darkside","Tales from the crypt",
                         "Creepshow","The Hitchhiker","Into the Dark","The Ray Bradbury Theater","American Horror Stories","Anthology"],
            "scifiday" :["Science-Fiction","Science Fiction","Sci-Fi"],
            "gijoe"    :["G.I. Joe","GI Joe"],
            "romance"  :["Valentine","Valentines","Valentine""s Day","Romance","Romcom","Love","Cupid"],
            "pokemon"  :["Pokémon","Pokemon"],
            "seuss"    :["Dr. Seuss","Dr Seuss","Lorox","Horton","Grinch"],
            "hitch"    :["Alfred Hitchcock"],
            "lotr"     :["Hobbit","Lord of the rings","LOTR","Tolkien"],
            "pulp"     :["Quentin Tarantino","Tarantino"],
            "startrek" :["Star Trek","Gene Roddenberry"],
            "aliens"   :["Alien vs. Predator","Aliens vs. Predator: Requiem","Prometheus","Alien: Covenant","Alien","Aliens","Alien 3","Alien: Resurrection","Predator","Predator 2","Predators"],
            "super"    :["Superhero","DC","Marvel","Batman","Superman","Spiderman","Spider-Man","Thor"],
            "starwars" :["Star Wars","Krieg der Sterne","Skywalker","Darth Vader","Jedi ","Ewoks","Boba Fett","Mandalorian" 
                         "Starwars","Yoda ","Obi-Wan","Kenobi","Millennium Falcon","Millenium Falke","Stormtrooper","Sturmtruppler", "Sith"],
            "zone"     :["The Twilight Zone","Twilight Zone"],
            "watson"   :["Sherlock","Holmes","Watson","Sher-lock"],
            "vampire"  :["Dracula","Vampire","Nosferatu","Vamp","Bloodsucker","Succubus"],
            "ghosts"   :["Ghostbusters"],
            "superman" :["Superman","Krypton","Supergirl","Louis & Clark","Superboy","Man of Steel","Smallville","Justice League"],
            "potter"   :["Harry Potter","Fantastic Beasts"],
            "spider"   :["Spider-Man","Spiderman","Peter Parker"],
            "ranger"   :["Power Rangers"],
            "batman"   :["Batman","Joker","Dark Knight"],
            "hobbit"   :["Hobbit"],
            "comic"    :["DC","Marvel","Batman","Superman","Spiderman","Spider-Man","Wonder woman"],
            "future"   :["Back to the Future"],
            "horror"   :["ужас","užas","rædsel","horror","φρίκη","õudus","kauhu","horreur","užas",
                         "borzalom","hryllingi","ホラー","siaubas","verschrikking","skrekk","przerażenie",
                         "groază","фильм ужасов","hrôza","grozo","Skräck","korku","жах","halloween"],
            "veterans" :["World War One","World War Two","V-Day","D-Day","WWI","WWII","Pearl Harbor","Dunkirk","War","World War",
                         "Vietnam","Warfare","Army","Navy","Naval","Marine","Air Force","Military","Soldier","Cadet","Officer","Korean War"],
            "tardis"   :["Tardis","Doctor Who","Dr. Who","Dr Who"],
            "disney"   :["Pixar","Disney","Mickey Mouse"],
            "marvel"   :["Marvel","Spiderman","Spider-Man","X-Men","Deadpool","The Avengers"],
            "xmas"     :["xmas","christmas","x-mas","santa claus","st. claus","happy holidays","st. nick","Weihnacht",
                         "fest der liebe","heilige nacht","heiliger abend","heiligabend","nikolaus","christkind","Noël",
                         "Meilleurs vœux","feliz navidad","joyeux noel","Natale","szczęśliwe święta","Veselé Vánoce",
                         "Vrolijk kerstfeest","Kerstmis","Boże Narodzenie","Kalėdos","Crăciun"]}
                                                
TVSHOW_XSP  = 'videodb://tvshows/titles/-1/-1/-1/-1/?xsp=%s'
MOVIE_XSP   = 'videodb://movies/titles/?xsp=%s'

EXCL_EXTRAS = [{"field":"season" ,"operator":"greaterthan","value":"0"},
               {"field":"episode","operator":"greaterthan","value":"0"}]
    
class Seasonal:
    def __init__(self):
        self.log('__init__')
        
                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getWeek(self):
        dt = datetime.datetime.now()
        adjusted_dom = dt.day + dt.replace(day=1).weekday()
        week = (adjusted_dom/7.0)
        if week > 4.0: return int(ceil(week))
        else:          return int(floor(week))


    def getMonth(self):
        return datetime.datetime.now().strftime('%B')


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
            holiday = SEASONS.get(month,{}).get(next,{})
            if holiday.get('keyword'): break
        self.log('getNearestHoliday, using fallback = %s, month = %s, current week = %s, using week = %s, found = %s'%(fallback, month, week, next, holiday))
        return holiday


    def buildSeasonal(self, citem, nearest=SETTINGS.getSettingBool('NEAREST_SEASON')):
        urls = []        
        if nearest: season = self.getNearestHoliday()
        else:       season = self.getCurrentHoliday()
        
        keyword = season.get('keyword','')
        if len(KEYWORDS.get(keyword,[])) > 0:
            for value in KEYWORDS.get(keyword,[]):
                for type in season.get('types',[]): #tv/movie
                    for field in season.get('fields',[]):    
                        param = {}
                        param["type"]  = {"tvshow":"episodes","movie":"movies"}[type]
                        param["order"] = {"direction"        :"ascending",
                                          "method"           :"random",
                                          "ignorearticle"    :True,
                                          "useartistsortname":True}

                        if type == 'tvshow' and field == 'title': field = 'tvshow'
                        if type == 'tvshow' and not SETTINGS.getSettingBool('Enable_Extras'): 
                            param.setdefault("rules",{}).setdefault("and",[]).extend(EXCL_EXTRAS)
                        param["order"]["method"] = season.get('method',{"tvshow":"episode","movie":"random"})[type]
                    
                        entry = {"operator":season.get('operator','contains')}
                        entry["field"] = field
                        entry["value"] = quoteString(value)
                        param.setdefault("rules",{}).setdefault("and",[]).append(entry)
                            
                        if   type == 'tvshow': urls.append('videodb://tvshows/titles/-1/-1/-1/-1/?xsp=%s'%(dumpJSON(param)))
                        elif type == 'movie':  urls.append('videodb://movies/titles/?xsp=%s'%(dumpJSON(param)))
       
        holiday = '%s%s'%(season.get('name',''),(' - %s'%(season.get('tagline')) if season.get('tagline','') else ''))
        self.log('buildSeasonal, returning holiday = %s, urls = %s'%(holiday,urls))
        return {'holiday':holiday, 'logo':(season.get('logo','') or citem['logo']), 'path': urls}
        
        
        # # TODO improve keywords by adding fields and operators to each keyword. ie. {'fields':['title','plot'],'operator':'contains','keywords':['Superman','Batman'],'types':['episodes','movies']},{'fields':['studio'],'operator':'is','keywords':['Marvel Studios','DC Studios'],'types':['episodes','movies']}
        # # KEYPARAMS = {'super': [{'fields':['title','plot'],'operator':'contains','keywords':['Superman','Batman'],'types':['episodes','movies']}]}
        # urls   = []
        # params = KEYPARAMS.get(season.get('keyword',''),[])
        # if params:
            # citem['holiday'] = '%s%s'%(season.get('name',''),(' - %s'%(season.get('tagline')) if season.get('tagline','') else ''))
            # citem['logo']    = (season.get('logo','') or citem['logo'])
            
            # for param in params:
                # url      = {}
                # operator = param.get('operator')
                # order    = param.get('order',{'direction':{'episodes':'ascending','movies':'ascending'},'method':{'episodes':'episode','movies':'random'}})
                # fields   = param.get('fields',[])
                # values   = param.get('keywords',[])
                # if not operator: continue
                # for type in param.get('types',[]):
                    # if type in TV_TYPES:
                        # path = TVSHOW_XSP
                        # if 'title' in fields: #unify "title" as movie/tv key; actual jsonrpc key for tv is "tvshow"
                            # fields.pop(fields.index('title'))
                            # fields.append('tvshow')
                        # if not SETTINGS.getSettingBool('Enable_Extras'): 
                            # url.setdefault("rules",{}).setdefault("and",[]).extend(EXCL_EXTRAS)
                    # else:
                        # path = MOVIE_XSP

                    # url["type"]  = type
                    # url["order"] = {"direction"        :order.get('direction')[type],
                                    # "method"           :order.get('method')[type],
                                    # "ignorearticle"    :True,
                                    # "useartistsortname":True}
                                    
                    

                    # for field in param.get('fields',[]):
                    # for value in param.get('keywords',[]):





                    # entry = {"operator":operator}
                    # entry["field"] = fields
                    # entry["value"] = quoteString(value)
                    # url.setdefault("rules",{}).setdefault("or",[]).append(entry)