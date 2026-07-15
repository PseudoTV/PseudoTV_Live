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
        self.id: str = id
        self.number: int = number
        self.name: str = name
        self.logo: str = logo
        self.group: list = group
        self.catchup: str = catchup
        self.radio: bool = radio
        self.favorite: bool = favorite
        self.realtime: bool = realtime
        self.media: str = media
        self.label: str = label
        self.url: str = url
        self.tvg-shift: str = tvg-shift
        self.x-tvg-url: str = x-tvg-url
        self.media-dir: str = media-dir
        self.media-size: str = media-size
        self.media-type: str = media-type
        self.catchup-source: str = catchup-source
        self.catchup-days: int = catchup-days
        self.catchup-correction: str = catchup-correction
        self.provider: str = provider
        self.provider-type: str = provider-type
        self.provider-logo: str = provider-logo
        self.provider-countries: list = provider-countries
        self.provider-languages: list = provider-languages
        self.x-playlist-type: str = x-playlist-type
        self.kodiprops: dict = kodiprops
        
#todo convert json to dataclasses https://dataclass-wizard.readthedocs.io/en/latest/