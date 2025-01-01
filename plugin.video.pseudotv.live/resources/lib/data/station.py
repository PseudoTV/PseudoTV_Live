  # Copyright (C) 2024 Lunatixz


# This file is part of PseudoTV Live.

# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
from globals   import *

class Station():
    def __init__(self):
        self.id                 = id
        self.number             = number
        self.name               = name
        self.logo               = logo
        self.group              = group
        self.catchup            = catchup
        self.radio              = radio
        self.favorite           = favorite
        self.realtime           = realtime
        self.media              = media
        self.label              = label
        self.url                = url
        self.tvg-shift          = tvg-shift
        self.x-tvg-url          = x-tvg-url
        self.media-dir          = media-dir
        self.media-size         = media-size
        self.media-type         = media-type
        self.catchup-source     = catchup-source
        self.catchup-days       = catchup-days
        self.catchup-correction = catchup-correction
        self.provider           = provider
        self.provider-type      = provider-type
        self.provider-logo      = provider-logo
        self.provider-countries = provider-countries
        self.provider-languages = provider-languages
        self.x-playlist-type    = x-playlist-type
        self.kodiprops          = kodiprops
        
#todo convert json to dataclasses https://dataclass-wizard.readthedocs.io/en/latest/