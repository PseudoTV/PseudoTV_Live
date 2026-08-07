#   Copyright (C) 2026 Lunatixz
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
"""Unified international content-rating normalization.

Every rating system Kodi can return (MPAA, VCHIP/TV, BBFC, FSK, CNC, ACB,
OFL C, CHVRS, Eirin, Kijkwijzer, KMRB, FPB, RTC, MTRCB, DJCTQ and any
numeric-age system such as IARC) is normalized to a canonical MPAA severity
so addon logic can reason about ratings uniformly.

Two representations are kept deliberately separate:

* ``local()``  — the user's local rating label (what they see in the UI,
  XMLTV guide and filler folder names). Never converted.
* ``rank()`` / ``toMPAA()`` — the canonical MPAA interpretation used by
  filter/reorder logic (e.g. RatingFilter).

Filler lookups must use ``local()`` so an international rating only ever
matches its own exact folder (a "FSK 16" rating hits the "FSK 16" folder,
never the MPAA "R" folder).
"""
import re

# Canonical MPAA severity ordering ('' = unrated/unknown, kept at 0 so an
# unrecognized label never gets filtered out).
MPAA_RANK = {'': 0, 'G': 1, 'PG': 2, 'PG-13': 3, 'R': 4, 'NC-17': 5, 'NR': 6}

# Named rating systems: system name -> {label: canonical MPAA label}.
_SYSTEMS = {
    'MPAA':  {'G': 'G', 'PG': 'PG', 'PG-13': 'PG-13', 'R': 'R', 'NC-17': 'NC-17',
              'NR': 'NR', 'X': 'NC-17'},
    'VCHIP': {'TV-Y': 'G', 'TV-Y7': 'PG', 'TV-G': 'G', 'TV-PG': 'PG',
              'TV-14': 'PG-13', 'TV-MA': 'R'},
    'BBFC':  {'U': 'G', 'UC': 'G', 'PG': 'PG', '12A': 'PG-13', '12': 'PG-13',
              '15': 'R', '18': 'NC-17', 'R18': 'NC-17'},
    'FSK':   {'0': 'G', '6': 'G', '12': 'PG-13', '16': 'R', '18': 'NC-17'},
    'CNC':   {'TP': 'G', '10': 'PG', '12': 'PG-13', '16': 'R', '18': 'NC-17'},
    'ACB':   {'G': 'G', 'PG': 'PG', 'M': 'PG-13', 'MA15+': 'R', 'R18+': 'NC-17',
              'X18+': 'NC-17'},
    'OFLC':  {'G': 'G', 'PG': 'PG', 'M': 'PG-13', 'R13': 'R', 'R15': 'R',
              'R16': 'R', 'R18': 'NC-17'},
    'CHVRS': {'G': 'G', 'PG': 'PG', '14A': 'PG-13', '18A': 'R', 'R': 'R', 'A': 'NC-17'},
    'EIRIN': {'G': 'G', 'PG12': 'PG-13', 'R15+': 'R', 'R18+': 'NC-17'},
    'KIJK':  {'AL': 'G', '6': 'G', '9': 'PG', '12': 'PG-13', '16': 'R'},
    'KMRB':  {'ALL': 'G', '12': 'PG-13', '15': 'R', '19': 'NC-17'},
    'FPB':   {'A': 'G', 'PG': 'PG', '10': 'PG', '13': 'PG-13', '16': 'R', '18': 'NC-17'},
    'RTC':   {'AA': 'G', 'A': 'G', 'B': 'PG', 'B15': 'PG-13', 'C': 'R', 'D': 'NC-17'},
    'MTRCB': {'G': 'G', 'PG': 'PG', 'R-13': 'PG-13', 'R-16': 'R', 'R-18': 'NC-17'},
    'DJCTQ': {'L': 'G', '10': 'PG', '12': 'PG-13', '14': 'R', '16': 'R', '18': 'NC-17'},
}

# Flattened label -> canonical MPAA. Shared numeric labels (6/12/16/18/...) are
# consistent across the systems that use them, so flattening is unambiguous.
_NAMED = {}
for _system, _labels in _SYSTEMS.items():
    for _label, _mpaa in _labels.items():
        _NAMED[_label] = _mpaa

# Minimum-age -> canonical MPAA (numeric/IARC-style ratings not in _NAMED).
_AGE_BANDS = [(0, 'G'), (7, 'PG'), (11, 'PG-13'), (14, 'R'), (17, 'NC-17')]

# Region aliases -> canonical ISO 3166-1 alpha-2 used for user-locale matching.
_REGION_ALIASES = {
    'UK': 'GB', 'EN': 'US', 'USA': 'US', 'UNITED STATES': 'US', 'ENGLAND': 'GB',
    'GREAT BRITAIN': 'GB', 'GERMANY': 'DE', 'DEUTSCHLAND': 'DE', 'FRANCE': 'FR',
    'ESPANA': 'ES', 'SPAIN': 'ES', 'ITALY': 'IT', 'AUSTRALIA': 'AU',
    'NEW ZEALAND': 'NZ', 'CANADA': 'CA', 'JAPAN': 'JP', 'NETHERLANDS': 'NL',
    'HOLLAND': 'NL', 'SOUTH KOREA': 'KR', 'KOREA': 'KR', 'SOUTH AFRICA': 'ZA',
    'MEXICO': 'MX', 'PHILIPPINES': 'PH', 'BRAZIL': 'BR', 'SWITZERLAND': 'CH',
    'ARGENTINA': 'AR',
}

# ISO region code -> rating system name (used for the XMLTV <rating system=>).
_REGION_TO_SYSTEM = {
    'US': 'MPAA', 'GB': 'BBFC', 'DE': 'FSK', 'FR': 'CNC', 'AU': 'ACB',
    'NZ': 'OFLC', 'CA': 'CHVRS', 'JP': 'EIRIN', 'NL': 'KIJK', 'KR': 'KMRB',
    'ZA': 'FPB', 'MX': 'RTC', 'PH': 'MTRCB', 'BR': 'DJCTQ',
}

_RATED = re.compile(r'^\s*rated\s+', re.IGNORECASE)
_TRAILING_REGION = re.compile(r'\s+/\s*[A-Z]{2,3}(?:\s*,\s*[A-Z]{2,3})*\s*$', re.IGNORECASE)
_TRAILING_PAREN = re.compile(r'\s*\([^)]*\)\s*$')
_PREFIXED = re.compile(r'^([A-Za-z]{2,3}(?:[_-][A-Za-z]{2,3})?|[A-Za-z][A-Za-z ]{2,}):\s*(.+)$')
_AGE_RE = re.compile(r'(\d+)')


def _norm_region(code: str) -> str:
    c = (code or '').upper().strip()
    return _REGION_ALIASES.get(c, c)


def _user_region() -> str:
    try:
        from variables import Globals
        lang = Globals._getLanguage()  # e.g. 'en-US', 'de-DE'
        if not isinstance(lang, str): return ''
        return lang.replace('_', '-').split('-')[-1].upper()
    except Exception:
        return ''


def _segments(raw) -> list:
    """Split a raw rating string into (region_code|None, value) pairs.

    Handles 'Rated PG-13', 'PG-13 / US', 'PG-13 (US)', 'US:PG-13',
    'US:PG-13/DE:FSK 16/CH:14' and bare labels like 'FSK 16' / 'TV-14'.
    """
    if not raw: return []
    raw = _RATED.sub('', str(raw).strip()).strip()
    raw = _TRAILING_REGION.sub('', raw)
    raw = _TRAILING_PAREN.sub('', raw)
    segs = []
    for part in raw.split('/'):
        part = part.strip()
        if not part: continue
        m = _PREFIXED.match(part)
        if m: segs.append((_norm_region(m.group(1)), m.group(2).strip()))
        else: segs.append((None, part))
    return segs


def _chosen(raw, region: str = None) -> tuple:
    """Pick the rating segment the user actually sees.

    Prefers the segment whose region matches the user's locale, then a bare
    (unprefixed) segment, then the first segment.
    """
    segs = _segments(raw)
    if not segs: return (None, '')
    region = _norm_region(region if region is not None else _user_region())
    for code, val in segs:
        if code and code == region: return (code, val)
    for code, val in segs:
        if code is None: return (None, val)
    return segs[0]


def local(raw, region: str = None) -> str:
    """The user's local rating label (never converted to MPAA).

    Example: 'US:PG-13/DE:FSK 16' -> 'FSK 16' for a German locale, 'PG-13' for
    a US locale. Falls back to the bare/first value for unknown locales.
    """
    return _chosen(raw, region)[1]


def toMPAA(raw, region: str = None) -> str:
    """Canonical MPAA label for a raw rating (G/PG/PG-13/R/NC-17/NR).

    Unknown labels are passed through unchanged (rank() then yields 0, so an
    unrecognized rating is never accidentally filtered).
    """
    return _label_to_mpaa(_chosen(raw, region)[1])


def _label_to_mpaa(label: str) -> str:
    label = str(label or '').upper().strip()
    if label in _NAMED: return _NAMED[label]
    m = _AGE_RE.search(label)  # numeric-age ratings (IARC/FSK style)
    if m:
        age = int(m.group(1))
        mpaa = 'G'
        for min_age, cand in _AGE_BANDS:
            if age >= min_age: mpaa = cand
        return mpaa
    return label


def rank(raw, region: str = None) -> int:
    """Severity 0-6: 0 unknown/unrated, 1 G ... 5 NC-17, 6 NR.

    Works for any international rating (FSK 16 -> R -> 4, BBFC 15 -> R -> 4).
    """
    return MPAA_RANK.get(toMPAA(raw, region), 0)


def system(raw, region: str = None) -> str:
    """Detected rating-system name for the XMLTV <rating system=> attribute.

    'VCHIP' for TV-* ratings, the named system for international ratings, and
    'MPAA' as the fallback.
    """
    code, val = _chosen(raw, region)
    val = val.upper()
    if code in _REGION_TO_SYSTEM: return _REGION_TO_SYSTEM[code]
    for sysname in _SYSTEMS:
        if val.startswith(sysname): return sysname
    if val.startswith('TV-'): return 'VCHIP'
    return 'MPAA'
