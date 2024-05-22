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

TV_QUERY    = {"path":"videodb://tvshows/titles/" ,"limit":"","sort":{},"filter":{},
               "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"}
               
MOVIE_QUERY = {"path":"videodb://movies/titles/"  ,"limit":"","sort":{},"filter":{},
               "method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie"  ,"key":"movies"}
               
SEASONS = {"January"   : {'1':{'name':"New Years Anthologies"   , 'tagline':"“You're traveling through another dimension...“"                 , 'keyword':'newyear'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://assets.stickpng.com/images/580b57fcd9996e24bc43c410.png'},
                          '2':{'name':"Science Fiction Week"    , 'tagline':"“Science fiction frees you to go anyplace and examine anything.“", 'keyword':'scifi'    , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://www.pngall.com/wp-content/uploads/6/Science-Fiction-PNG-Free-Download.png'},
                          '3':{'name':"J.R.R. Tolkien Week"     , 'tagline':"“One ring to rule them all.“"                                    , 'keyword':'lotr'     , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://www.pngall.com/wp-content/uploads/12/Lord-Of-The-Rings-Logo-PNG-Picture.png'},
                          '4':{'name':'Lego Week'               , 'tagline':"“With a bucket of Lego, you can tell any story.“"                , 'keyword':'lego'     , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://pngimg.com/d/lego_PNG99.png'},
                          '5':{'name':''                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},

           "February"  : {'1':{'name':"G.I. Joe Week"           , 'tagline':"“A Real American Hero!“"                                         , 'keyword':'gijoe'    , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://preview.redd.it/zul0o3zwo2r71.png?width=640&crop=smart&auto=webp&s=4ad37682d57f808ce82dba51c9aeaebce5b59258'}, 
                          '2':{'name':"Valentines Week"         , 'tagline':"“Love is in the air!“"                                           , 'keyword':'romance'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://icons.iconarchive.com/icons/designbolts/valentine/512/Happy-valentines-day-icon.png'},
                          '3':{'name':"Pokémon Week"            , 'tagline':"“Gotta Catch ""em All“"                                          , 'keyword':'pokemon'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://w7.pngwing.com/pngs/427/428/png-transparent-pokemon-logo-pokemon-go-pikachu-logo-ash-ketchum-pokemon-go-text-banner-sign.png'},
                          '4':{'name':"Superman Week"           , 'tagline':"“Truth, justice, and the American way.“"                         , 'keyword':'superman' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Superman_S_symbol.svg/2560px-Superman_S_symbol.svg.png'},
                          '5':{'name':''                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                      
           "March"     : {'1':{'name':"Dr. Seuss Week"          , 'tagline':"“Think and wonder. Wonder and think.”"                           , 'keyword':'seuss'    , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://static.wikia.nocookie.net/logopedia/images/9/90/Dr._Seuss.svg/revision/latest?cb=20180125222130',}, 
                          '2':{'name':"Alfred Hitchcock Week"   , 'tagline':"“Always make the audience suffer...”"                            , 'keyword':'hitchcock', 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://upload.wikimedia.org/wikipedia/fr/6/6b/Alfred_Hitchcock_pr%C3%A9sente.png'},
                          '3':{'name':"St. Patrick's Week"      , 'tagline':"“May the luck of the Irish lead to happiest heights...”"         , 'keyword':'patrick'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://seeklogo.com/images/H/happy-st-patricks-day-logo-AFF883C309-seeklogo.com.png'},
                          '4':{'name':"J.R.R. Tolkien Week"     , 'tagline':"“One ring to rule them all.“"                                    , 'keyword':'lotr'     , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://www.pngall.com/wp-content/uploads/12/Lord-Of-The-Rings-Logo-PNG-Picture.png'},
                          '5':{'name':"Quentin Tarantino Week"  , 'tagline':"“If you just love movies enough, you can make a good one.”"      , 'keyword':'quentin'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://rat.in.ua/wp-content/uploads/2019/11/4758-Written-and-Directed-by-Quentin-Tarantino.png'}},
                      
           "April"     : {'1':{'name':"Star Trek Week"          , 'tagline':"“To Boldly Go...“"                                               , 'keyword':'startrek' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://assets.stickpng.com/images/613794434b96600004f67704.png'}, 
                          '2':{'name':"Shakespeare Week"        , 'tagline':"“Non Sans Droict“"                                               , 'keyword':'othello'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '3':{'name':"Superhero Week"          , 'tagline':"“I Can Do This All Day!“"                                        , 'keyword':'super'    , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '4':{'name':"Alien Week"              , 'tagline':"“In space, no one can hear you scream.“"                         , 'keyword':'aliens'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '5':{'name':"Star Wars Week"          , 'tagline':"“May the force be with you.“"                                    , 'keyword':'starwars' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                          
           "May"       : {'1':{'name':"Star Wars Week"          , 'tagline':"“May the force be with you.“"                                    , 'keyword':'starwars' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://assets.stickpng.com/thumbs/602176580ad3230004b93c22.png'},
                          '2':{'name':"Twilight Zone Week"      , 'tagline':"“You are about to enter another dimension...“"                   , 'keyword':'twilight' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://media.themoviedb.org/t/p/w500/4xJR8vKOczmaIYZ7BbWlEApqR0m.png'},
                          '3':{'name':"Sherlock Holmes Week"    , 'tagline':"“The Game is Afoot!“"                                            , 'keyword':'watson'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://picfiles.alphacoders.com/123/123200.png'},
                          '4':{'name':"Dracula Week"            , 'tagline':"“Fidelis et mortem“"                                             , 'keyword':'vampire'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://assets.stickpng.com/thumbs/59f876c13cec115efb36237e.png'},
                          '5':{'name':""                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                          
           "June"      : {'1':{'name':""                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '2':{'name':"Ghostbusters Week"       , 'tagline':"“Who You Gonna Call?“"                                           , 'keyword':'ghosts'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://images.fineartamerica.com/images/artworkimages/medium/3/ghostbusters-original-logo-harlem-nellie-transparent.png'},
                          '3':{'name':"Superman Week"           , 'tagline':"“Truth, justice, and the American way.“"                         , 'keyword':'superman' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Superman_shield.svg/1200px-Superman_shield.svg.png'},
                          '4':{'name':''                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '5':{'name':''                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                          
           "July"      : {'1':{'name':''                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '2':{'name':''                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '3':{'name':"Disney Week"             , 'tagline':"“Where Dreams Come True.“"                                       , 'keyword':'disney'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '4':{'name':"Harry Potter Week"       , 'tagline':"“Draco Dormiens Nunquam Titillandus“"                            , 'keyword':'potter'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '5':{'name':"Harry Potter Week"       , 'tagline':"“Draco Dormiens Nunquam Titillandus“"                            , 'keyword':'potter'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                          
           "August"    : {'1':{'name':"Spiderman Week"          , 'tagline':"“with great power comes great responsibility“"                   , 'keyword':'spider'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '2':{'name':""                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '3':{'name':"SpongeBob Week"          , 'tagline':"“Three hours later“"                                             , 'keyword':'sponge'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '4':{'name':"Power Rangers Week"      , 'tagline':"“Everyone gets to be a Ranger!”"                                 , 'keyword':'ranger'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '5':{'name':''                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                          
           "September" : {'1':{'name':"Star Trek Week"          , 'tagline':"“To Boldly Go...“"                                               , 'keyword':'startrek' , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://assets.stickpng.com/images/613794434b96600004f67704.png'},
                          '2':{'name':"Batman Week"             , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '3':{'name':"Hobbit Week"             , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '4':{'name':"Comic Book Week"         , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '5':{'name':"Comic Book Week"         , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                          
           "October"   : {'1':{'name':"Willy Wonka Week"        , 'tagline':"“The Suspense Is Terrible. I Hope It’ll Last.”"                  , 'keyword':'wonka'    , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '2':{'name':"Back to the Future Week" , 'tagline':"“Great Scott!”"                                                  , 'keyword':'future'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '3':{'name':""                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '4':{'name':"Halloween Season"        , 'tagline':"Spooky Suggestions"                                              , 'keyword':'horror'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '5':{'name':"Halloween Season"        , 'tagline':"Spooky Suggestions"                                              , 'keyword':'horror'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}},
                          
           "November"  : {'1':{'name':""                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '2':{'name':"Veterans Week"           , 'tagline':"“Honoring all who served”"                                       , 'keyword':'heros'    , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '3':{'name':"Doctor Who Week"         , 'tagline':"“Run!”"                                                          , 'keyword':'who'      , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '4':{'name':"Thanksgiving Week"       , 'tagline':''                                                                , 'keyword':'turkey'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '5':{'name':"Marvel Week"             , 'tagline':"“Excelsior!”"                                                    , 'keyword':'marvel'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''}}, 
                          
           "December"  : {'1':{'name':"Marvel Week"             , 'tagline':"“Excelsior!”"                                                    , 'keyword':'marvel'   , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '2':{'name':""                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '3':{'name':""                        , 'tagline':''                                                                , 'keyword':''         , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '4':{'name':"Holiday Season"          , 'tagline':"“Tis the season“"                                                , 'keyword':'xmas'     , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':''},
                          '5':{'name':"New Years Anthologies"   , 'tagline':"“You're traveling through another dimension...“"                 , 'keyword':'newyear'  , 'query':[TV_QUERY,MOVIE_QUERY], 'logo':'https://cdn-icons-png.flaticon.com/512/3763/3763123.png'}}}

KEYWORDS = {"":{},
            "hitchcock":{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["Alfred Hitchcock"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Alfred Hitchcock"]}]}]}}],
                         "movies"  : [{"sort":{"method":"random", "order":"ascending"},"filter":{"and":[{"or" :[{"field":"director","operator":"contains","value":["Alfred Hitchcock"]},
                                                                                                                {"field":"writers" ,"operator":"contains","value":["Alfred Hitchcock"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Alfred Hitchcock"]}]}]}}]},
                                                                                                                
            "patrick"  :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["It's Always Sunny"]}]}]}},
                                      {"sort":{"method":"random" ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"plot"    ,"operator":"contains","value":["St. Patrick","Leprechaun","Irish","Luck","Lucky","Gold","Shamrock"]}]}]}}],
                         "movies"  : [{"sort":{"method":"random" ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"plot"    ,"operator":"contains","value":["St. Patrick","Leprechaun","Irish","Luck","Lucky","Gold","Shamrock"]}]}]}}]},
            
            "lotr"     :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["Tolkien","Hobbit","Lord of the Rings"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Tolkien","Hobbit","Lord of the Rings"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"contains","value":["Tolkien","Hobbit","Lord of the Rings"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Tolkien","Hobbit","Lord of the Rings"]}]}]}}]},
            
            "quentin"  :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"director","operator":"contains","value":["Quentin Tarantino"]},
                                                                                                                {"field":"writers" ,"operator":"contains","value":["Quentin Tarantino"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Quentin Tarantino"]}]}]}}],
                         "movies"  : [{"sort":{"method":"random" ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"director","operator":"contains","value":["Quentin Tarantino"]},
                                                                                                                {"field":"writers" ,"operator":"contains","value":["Quentin Tarantino"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Quentin Tarantino"]}]}]}}]},
                                                                                                                
            "startrek" :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["Star Trek"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Star Trek"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"contains","value":["Star Trek"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Star Trek"]}]}]}}]},
                                                                                                                
            "othello"  :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["William Shakespeare","Shakespeare"]},
                                                                                                                {"field":"writers" ,"operator":"contains","value":["William Shakespeare","Shakespeare"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["William Shakespeare","Shakespeare"]}]}]}}],
                         "movies"  : [{"sort":{"method":"random" ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"contains","value":["William Shakespeare","Shakespeare"]},
                                                                                                                {"field":"writers" ,"operator":"contains","value":["William Shakespeare","Shakespeare"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["William Shakespeare","Shakespeare"]}]}]}}]},
                                                                                                                
            "super"    :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"studio"  ,"operator":"contains","value":["Marvel","DC"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Superhero"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"studio"  ,"operator":"contains","value":["Marvel","DC"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Superhero"]}]}]}}]},
                                                                                                                
            "aliens"   :{"movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"is"      ,"value":["TED 2023","Prometheus","Alien: Covenant","Alien","Alien: Isolation","Alien: Out of the Shadows","Alien: Romulus","Aliens","Aliens: Colonial Marines","Fire and Stone","Alien3","Alien³","Aliens: Dark Descent","Aliens: Fireteam Elite","Aliens: Phalanx","Alien Resurrection"]},
                                                                                                                {"field":"title"   ,"operator":"is"      ,"value":["Predator","Predator 2","Predators","The Predator","Prey","Badlands","Alien vs. Predator","Aliens vs. Predator: Requiem"]}]}]}}]},
                                                                                                                
            "starwars" :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["Star Wars"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Star Wars"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"contains","value":["Star Wars"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Star Wars"]}]}]}}]},
            
            "twilight" :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["Twilight Zone", "Rod Serling"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Twilight Zone", "Rod Serling"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"contains","value":["Twilight Zone", "Rod Serling"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Twilight Zone", "Rod Serling"]}]}]}}]},
            
            "watson"   :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["Enola Holmes", "Sherlock", "Sher-lock", "Sherlock Holmes", "Arthur Conan Doyle"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Enola Holmes", "Sherlock", "Sher-lock", "Sherlock Holmes", "Arthur Conan Doyle"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"contains","value":["Enola Holmes", "Sherlock", "Sher-lock", "Sherlock Holmes", "Arthur Conan Doyle"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Enola Holmes", "Sherlock", "Sher-lock", "Sherlock Holmes", "Arthur Conan Doyle"]}]}]}}]},
            
            "vampire"  :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["Vampire", "Dracula" ,"Nosferatu"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Vampire", "Dracula" ,"Nosferatu", "Vamp", "Bloodsucker", "Vampirism"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"contains","value":["Vampire", "Dracula" ,"Nosferatu"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Vampire", "Dracula" ,"Nosferatu", "Vamp", "Bloodsucker", "Vampirism"]}]}]}}]},
            
            "ghosts"   :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["Ghostbusters"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Ghostbusters"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"contains","value":["Ghostbusters"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Ghostbusters"]}]}]}}]},
            
            "superman" :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["Superman"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Superman"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"contains","value":["Superman"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Superman"]}]}]}}]},
            }
                       
     
     
# KEYWORDS = {"newyear"  :["The Twilight Zone","Black-Mirror","Black Mirror","Outer Limits","Amazing Stories","Tales from the Darkside","Tales from the crypt",
                         # "Creepshow","The Hitchhiker","Into the Dark","The Ray Bradbury Theater","American Horror Stories","Anthology"],
            # "scifiday" :["Science-Fiction","Science Fiction","Sci-Fi"],
            # "gijoe"    :["G.I. Joe","GI Joe"],
            # "romance"  :["Valentine","Valentines","Valentine""s Day","Romance","Romcom","Love","Cupid"],
            # "pokemon"  :["Pokémon","Pokemon"],
            # "seuss"    :["Dr. Seuss","Dr Seuss","Lorox","Horton","Grinch"],
            # "hitch"    :["Alfred Hitchcock"],
            # "lotr"     :["Hobbit","Lord of the rings","LOTR","Tolkien"],
            # "pulp"     :["Quentin Tarantino","Tarantino"],
            # "startrek" :["Star Trek","Gene Roddenberry"],
            # "aliens"   :["Alien vs. Predator","Aliens vs. Predator: Requiem","Prometheus","Alien: Covenant","Alien","Aliens","Alien 3","Alien: Resurrection","Predator","Predator 2","Predators"],
            # "super"    :["Superhero","DC","Marvel","Batman","Superman","Spiderman","Spider-Man","Thor"],
            # "starwars" :["Star Wars","Krieg der Sterne","Skywalker","Darth Vader","Jedi ","Ewoks","Boba Fett","Mandalorian" 
                         # "Starwars","Yoda ","Obi-Wan","Kenobi","Millennium Falcon","Millenium Falke","Stormtrooper","Sturmtruppler", "Sith"],
            # "zone"     :["The Twilight Zone","Twilight Zone"],
            # "watson"   :["Sherlock","Holmes","Watson","Sher-lock"],
            # "vampire"  :["Dracula","Vampire","Nosferatu","Vamp","Bloodsucker","Succubus"],
            # "ghosts"   :["Ghostbusters"],
            # "superman" :["Superman","Krypton","Supergirl","Louis & Clark","Superboy","Man of Steel","Smallville","Justice League"],
            # "potter"   :["Harry Potter","Fantastic Beasts"],
            # "spider"   :["Spider-Man","Spiderman","Peter Parker"],
            # "ranger"   :["Power Rangers"],
            # "batman"   :["Batman","Joker","Dark Knight"],
            # "hobbit"   :["Hobbit"],
            # "comic"    :["DC","Marvel","Batman","Superman","Spiderman","Spider-Man","Wonder woman"],
            # "future"   :["Back to the Future"],
            # "horror"   :["ужас","užas","rædsel","horror","φρίκη","õudus","kauhu","horreur","užas",
                         # "borzalom","hryllingi","ホラー","siaubas","verschrikking","skrekk","przerażenie",
                         # "groază","фильм ужасов","hrôza","grozo","Skräck","korku","жах","halloween"],
            # "veterans" :["World War One","World War Two","V-Day","D-Day","WWI","WWII","Pearl Harbor","Dunkirk","War","World War",
                         # "Vietnam","Warfare","Army","Navy","Naval","Marine","Air Force","Military","Soldier","Cadet","Officer","Korean War"],
            # "tardis"   :["Tardis","Doctor Who","Dr. Who","Dr Who"],
            # "disney"   :["Pixar","Disney","Mickey Mouse"],
            # "marvel"   :["Marvel","Spiderman","Spider-Man","X-Men","Deadpool","The Avengers"],
            # "xmas"     :["xmas","christmas","x-mas","santa claus","st. claus","happy holidays","st. nick","Weihnacht",
                         # "fest der liebe","heilige nacht","heiliger abend","heiligabend","nikolaus","christkind","Noël",
                         # "Meilleurs vœux","feliz navidad","joyeux noel","Natale","szczęśliwe święta","Veselé Vánoce",
                         # "Vrolijk kerstfeest","Kerstmis","Boże Narodzenie","Kalėdos","Crăciun"]}
          
            # # 'pokemon'  :['Pokémon','Pokemon'],
            # # 'seuss'    :['Dr. Seuss','Dr Seuss','Lorox','Horton','Grinch'],
            # # 'hitch'    :['Alfred Hitchcock'],
            # # 'lotr'     :['Hobbit','Lord of the rings','LOTR','Tolkien'],
            # # 'pulp'     :["Quentin Tarantino","Tarantino"],
            # # 'startrek' :['Star Trek',"Gene Roddenberry"],
            # # 'aliens'   :['Alien vs. Predator','Aliens vs. Predator: Requiem','Prometheus','Alien: Covenant','Alien','Aliens','Alien 3','Alien: Resurrection','Predator','Predator 2','Predators'],
            # # 'super'    :['Superhero','DC','Marvel','Batman','Superman','Spiderman','Spider-Man','Thor'],
            # # 'starwars' :['Star Wars','Krieg der Sterne','Skywalker','Darth Vader','Jedi ','Ewoks','Boba Fett','Mandalorian' 
                         # # 'Starwars','Yoda ','Obi-Wan','Kenobi','Millennium Falcon','Millenium Falke','Stormtrooper','Sturmtruppler', 'Sith'],
            # # 'zone'     :['The Twilight Zone','Twilight Zone'],
            # # 'watson'   :['Sherlock','Holmes','Watson','Sher-lock'],
            # # 'vampire'  :['Dracula','Vampire','Nosferatu','Vamp','Bloodsucker','Succubus'],
            # # 'ghosts'   :['Ghostbusters'],
            # # 'superman' :['Superman','Krypton','Supergirl','Louis & Clark','Superboy','Man of Steel','Smallville','Justice League'],
            # # 'potter'   :['Harry Potter','Fantastic Beasts'],
            # # 'spider'   :['Spider-Man','Spiderman','Peter Parker'],
            # # 'ranger'   :['Power Rangers'],
            # # 'batman'   :['Batman','Joker','Dark Knight'],
            # # 'hobbit'   :['Hobbit'],
            # # 'comic'    :['DC','Marvel','Batman','Superman','Spiderman','Spider-Man','Wonder woman'],
            # # 'future'   :['Back to the Future'],
            # # 'horror'   :['ужас','užas','rædsel','horror','φρίκη','õudus','kauhu','horreur','užas',
                         # # 'borzalom','hryllingi','ホラー','siaubas','verschrikking','skrekk','przerażenie',
                         # # 'groază','фильм ужасов','hrôza','grozo','Skräck','korku','жах','halloween'],
            # # 'veterans' :['World War One','World War Two','V-Day','D-Day','WWI','WWII','Pearl Harbor','Dunkirk','War','World War',
                         # # 'Vietnam','Warfare','Army','Navy','Naval','Marine','Air Force','Military','Soldier','Cadet','Officer','Korean War'],
            # # 'tardis'   :['Tardis','Doctor Who','Dr. Who','Dr Who'],
            # # 'disney'   :['Pixar','Disney','Mickey Mouse'],
            # # 'marvel'   :['Marvel','Spiderman','Spider-Man','X-Men','Deadpool','The Avengers'],
            # # 'xmas'     :['xmas','christmas','x-mas','santa claus','st. claus','happy holidays','st. nick','Weihnacht',
                         # # 'fest der liebe','heilige nacht','heiliger abend','heiligabend','nikolaus','christkind','Noël',
                         # # 'Meilleurs vœux','feliz navidad','joyeux noel','Natale','szczęśliwe święta','Veselé Vánoce',
                         # # 'Vrolijk kerstfeest','Kerstmis','Boże Narodzenie','Kalėdos','Crăciun']
                         # }
                              