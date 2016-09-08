#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2011-2014 Martijn Kaijser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#

#import modules
import xbmc
import xbmcaddon

LANGUAGES = {'Albanian' : 'sq',
            'Arabic'    : 'ar',
            'Belarusian': 'hy',
            'Bosnian'   : 'bs',
            'Bulgarian' : 'bg',
            'Catalan'   : 'ca',
            'Chinese'   : 'zh',
            'Croatian'  : 'hr',
            'Czech'     : 'cs',
            'Danish'    : 'da',
            'Dutch'     : 'nl',
            'English'   : 'en',
            'Estonian'  : 'et',
            'Persian'   : 'fa',
            'Finnish'   : 'fi',
            'French'    : 'fr',
            'German'    : 'de',
            'Greek'     : 'el',
            'Hebrew'    : 'he',
            'Hindi'     : 'hi',
            'Hungarian' : 'hu',
            'Icelandic' : 'is',
            'Indonesian': 'id',
            'Italian'   : 'it',
            'Japanese'  : 'ja',
            'Korean'    : 'ko',
            'Latvian'   : 'lv',
            'Lithuanian': 'lt',
            'Macedonian': 'mk',
            'Norwegian' : 'no',
            'Polish'    : 'pl',
            'Portuguese': 'pt',
            'Portuguese (Brazil)': 'pb',
            'Romanian'  : 'ro',
            'Russian'   : 'ru',
            'Serbian'   : 'sr',
            'Slovak'    : 'sk',
            'Slovenian' : 'sl',
            'Spanish'   : 'es',
            'Swedish'   : 'sv',
            'Thai'      : 'th',
            'Turkish'   : 'tr',
            'Ukrainian' : 'uk',
            'Vietnamese': 'vi',
            'BosnianLatin': 'bs',
            'Farsi'     : 'fa',
            'Serbian (Cyrillic)': 'sr',
            'Chinese (Traditional)' : 'zh',
            'Chinese (Simplified)'  : 'zh'}
       
def get_abbrev(lang_string):
    try:
        language_abbrev = xbmc.convertLanguage(lang_string, xbmc.ISO_639_1)
    except:
        language_abbrev = REAL_SETTINGS.getSetting('preferred_language')
    if language_abbrev in LANGUAGES:
        return LANGUAGES[language_abbrev]
    else:
        language_abbrev = 'en' ### Default to English if conversion fails
    return language_abbrev
    
def get_language(abbrev):    
    try:
        lang_string = (key for key,value in LANGUAGES.items() if value == abbrev).next()
    except:
        lang_string = xbmc.convertLanguage(abbrev, xbmc.ENGLISH_NAME)
    if not lang_string:
        lang_string = 'n/a'
    return lang_string