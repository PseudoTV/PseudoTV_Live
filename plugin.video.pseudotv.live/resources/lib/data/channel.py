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

class Channel():
    def __init__(self, id: str="", type: str="", number: int=0, name: str="", logo: str="", path: list=[], group: list=[], rules: list=[], catchup: str="vod", radio: bool=False, favorite: bool=False):
        self.id       = id
        self.type     = type
        self.number   = number
        self.name     = name
        self.logo     = logo
        self.path     = path
        self.group    = group
        self.rules    = rules
        self.catchup  = catchup
        self.radio    = radio
        self.favorite = favorite


#todo convert json to dataclasses https://dataclass-wizard.readthedocs.io/en/latest/