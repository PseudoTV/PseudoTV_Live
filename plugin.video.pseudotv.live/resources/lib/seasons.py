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

KEYWORDS = {""         :{},
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
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"  ,"operator":"contains","value":["Tolkien","Hobbit","Lord of the Rings"]},
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
                                                                                                                
            "super"    :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tag"     ,"operator":"contains","value":["Superhero","Marvel","DC"]},
                                                                                                                {"field":"studio"  ,"operator":"contains","value":["Marvel","DC"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Superhero"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"tag"     ,"operator":"contains","value":["Superhero","Marvel","DC"]},
                                                                                                                {"field":"studio"  ,"operator":"contains","value":["Marvel","DC"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Superhero"]}]}]}}]},
                                                                                                                
            "aliens"   :{"movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"is"      ,"value":["TED 2023","Prometheus","Alien: Covenant","Alien","Alien: Isolation","Alien: Out of the Shadows","Alien: Romulus","Aliens","Aliens: Colonial Marines","Fire and Stone","Alien3","Alien³","Aliens: Dark Descent","Aliens: Fireteam Elite","Aliens: Phalanx","Alien Resurrection"]},
                                                                                                                {"field":"title"   ,"operator":"is"      ,"value":["Predator","Predator 2","Predators","The Predator","Prey","Badlands","Alien vs. Predator","Aliens vs. Predator: Requiem"]}]}]}}]},
                                                                                                                
            "starwars" :{"episodes": [{"sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"or" :[{"field":"tvshow"  ,"operator":"contains","value":["Star Wars"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Star Wars"]}]}]}}],
                         "movies"  : [{"sort":{"method":"year"   ,"order":"ascending"},"filter":{"and":[{"or" :[{"field":"title"   ,"operator":"contains","value":["Star Wars"]},
                                                                                                                {"field":"plot"    ,"operator":"contains","value":["Star Wars"]}]}]}}]},
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
                              