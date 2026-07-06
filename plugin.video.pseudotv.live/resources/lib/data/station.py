  # Copyright (C) 2025 Lunatixz


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
from variables import *

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
        self.tvg_shift          = tvg_shift
        self.x_tvg_url          = x_tvg_url
        self.media_dir          = media_dir
        self.media_size         = media_size
        self.media_type         = media_type
        self.catchup_source     = catchup_source
        self.catchup_days       = catchup_days
        self.catchup_correction = catchup_correction
        self.provider           = provider
        self.provider_type      = provider_type
        self.provider_logo      = provider_logo
        self.provider_countries = provider_countries
        self.provider_languages = provider_languages
        self.x_playlist_type    = x_playlist_type
        self.kodiprops          = kodiprops
        
#todo convert json to dataclasses https://dataclass-wizard.readthedocs.io/en/latest/