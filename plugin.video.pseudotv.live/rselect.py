#   Copyright (C) 2020 Lunatixz
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
#modified from <addon id="script.image.resource.select" name="Image Resource Select Addon" version="3.0.2" provider-name="ronie">

from resources.lib.globals     import *

ADDON   = REAL_SETTINGS
ADDONID = ADDON_ID
CWD     = ADDON_PATH

class Main():
    def __init__(self, *args, **kwargs):
        log('script started')
        params = kwargs['params']
        TYPE, PROP = self._parse_argv(params)
        if TYPE and PROP:
            ITEMS = self._get_addons(TYPE)
            self._select(ITEMS, TYPE, PROP)
        log('script stopped')

    def _parse_argv(self, params):
        log('params: %s' % str(params))
        TYPE = params.get('type', '')
        PROP = params.get('property', '')
        return TYPE, PROP

    def _get_addons(self, TYPE):
        listitems = []
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"type": "kodi.resource.images", "properties": ["name", "summary", "thumbnail", "path"]}, "id": 1}')
        json_response = json.loads(json_query)
        if 'result' in json_response and (json_response['result'] != None) and 'addons' in json_response['result']:
            addons = json_response['result']['addons']
            for item in sorted(addons, key=itemgetter('name')):
                if item['addonid'].startswith(TYPE):
                    name = item['name']
                    icon = item['thumbnail']
                    addonid = item['addonid']
                    path = item['path']
                    summary = item['summary']
                    extension, subfolders = self._get_data(path)
                    listitem = xbmcgui.ListItem(label=name, label2=addonid)
                    listitem.setArt({'icon':'DefaultAddonImages.png', 'thumb':icon})
                    listitem.setProperty('extension', extension)
                    listitem.setProperty('subfolders', subfolders)
                    listitem.setProperty('Addon.Summary', summary)
                    listitems.append(listitem)
        return listitems

    def _get_data(self, path):
        infoxml = os.path.join(path, 'info.xml')
        try:
            info = xbmcvfs.File(infoxml)
            data = info.read()
            info.close()
            xmldata = parseString(data)
            extension = xmldata.documentElement.getElementsByTagName('format')[0].childNodes[0].data
            subfolders = xmldata.documentElement.getElementsByTagName('subfolders')[0].childNodes[0].data
            return extension, subfolders
        except:
            return 'png', 'false'

    def _select(self, addonlist, category, string):
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(15109))
        listitem.setArt({'icon':'DefaultAddon.png'})
        addonlist.insert(0, listitem)
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(21452))
        listitem.setProperty('more', 'true')
        addonlist.append(listitem)
        num = xbmcgui.Dialog().select(xbmc.getLocalizedString(424), addonlist, useDetails=True)
        if num == 0:
            xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.name'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.path'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.ext'))
            xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.multi'))
        elif num > 0:
            item = addonlist[num]
            if item.getProperty('more') == 'true':
                xbmc.executebuiltin('ActivateWindow(AddonBrowser, addons://repository.xbmc.org/kodi.resource.images/,return)')
            else:
                name = item.getLabel()
                addonid = item.getLabel2()
                extension = '.%s' % item.getProperty('extension')
                subfolders = item.getProperty('subfolders')
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((string + '.name'), name))
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((string + '.path'), 'resource://%s/' % addonid))
                if subfolders == 'true':
                    xbmc.executebuiltin('Skin.SetBool(%s)' % (string + '.multi'))
                    xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.ext'))
                else:
                    xbmc.executebuiltin('Skin.Reset(%s)' % (string + '.multi'))
                    xbmc.executebuiltin('Skin.SetString(%s,%s)' % ((string + '.ext'), extension))

if (__name__ == '__main__'):
    try:    params = dict(arg.split('=') for arg in sys.argv[ 1 ].split('&'))
    except: params = {}
    Main(params=params)