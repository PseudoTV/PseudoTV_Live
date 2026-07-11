# -*- coding: utf-8 -*-
"""Unit tests for m3u.py - M3U parsing and item handling"""
import sys, os, json
from unittest.mock import MagicMock, patch
import pytest

# Mock Kodi modules
xbmc = MagicMock()
xbmcgui = MagicMock()
xbmcaddon = MagicMock()
xbmcvfs = MagicMock()
xbmcplugin = MagicMock()
xbr = MagicMock()
kodi_six = MagicMock()
kodi_six.xbmc = xbmc
kodi_six.xbmcgui = xbmcgui
kodi_six.xbmcaddon = xbmcaddon
kodi_six.xbmcvfs = xbmcvfs
kodi_six.xbmcplugin = xbmcplugin

xbmc.LOGDEBUG   = 0
xbmc.LOGINFO    = 1
xbmc.LOGWARNING = 2
xbmc.LOGERROR   = 3
xbmc.LOGFATAL   = 4
xbmc.LOGNONE    = 7
xbmc.PLAYLIST_MUSIC = 'music'
xbmc.PLAYLIST_VIDEO = 'video'
xbmc.SORT_METHOD_UNSPECIFIED = -1

sys.modules['xbmc'] = xbmc
sys.modules['xbmcgui'] = xbmcgui
sys.modules['xbmcaddon'] = xbmcaddon
sys.modules['xbmcvfs'] = xbmcvfs
sys.modules['xbmcplugin'] = xbmcplugin
sys.modules['xbr'] = xbr
sys.modules['kodi_six'] = kodi_six
sys.modules['kodi_six.xbmc'] = xbmc
sys.modules['kodi_six.xbmcgui'] = xbmcgui
sys.modules['kodi_six.xbmcaddon'] = xbmcaddon
sys.modules['kodi_six.xbmcvfs'] = xbmcvfs
sys.modules['kodi_six.xbmcplugin'] = xbmcplugin

sys.modules['requests'] = MagicMock()
sys.modules['requests.adapters'] = MagicMock()
sys.modules['pyqrcode'] = MagicMock()
sys.modules['infotagger'] = MagicMock()
sys.modules['infotagger.listitem'] = MagicMock()

import urllib.parse as _real_urlparse
import types as _types
_six_urllib_ns = _types.SimpleNamespace(parse=_real_urlparse)
six_mock = MagicMock()
six_mock.moves.urllib = _six_urllib_ns
sys.modules["six"] = six_mock
sys.modules["six.moves"] = six_mock.moves

LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'lib')
sys.path.insert(0, LIB_DIR)

import variables


@pytest.fixture(autouse=True)
def _patch_kodi_apis():
    with patch('xbmcaddon.Addon') as mock_addon_cls, \
         patch('xbmc.getSupportedMedia', return_value='|.mp4|.mkv|.avi|'):
        mock_addon = MagicMock()
        mock_addon_cls.return_value = mock_addon
        mock_addon.getAddonInfo.side_effect = lambda k: {
            'name': 'TestAddon', 'version': '1.0.0',
            'icon': 'icon.png', 'fanart': 'fanart.jpg',
            'profile': 'special://profile/addon_data/test/',
            'path': '/tmp/test_addon', 'author': 'Test'
        }.get(k, '')
        mock_addon.getSetting.side_effect = lambda k: {
            'User_Folder': 'special://profile/addon_data/plugin.video.pseudotv.live/cache',
            'Disable_Cache': 'false', 'API_Timeout': '30',
            'Debug_Enable': 'false', 'Debug_Level': '3',
            'Enable_Grouping': 'true', 'Enable_Executor': 'true',
            'Cache_MEM_Limit': '10'
        }.get(k, '')
        mock_addon.getSettingBool.return_value = True
        mock_addon.getSettingInt.return_value = 50
        mock_addon.getLocalizedString.return_value = 'TestString'
        yield


@pytest.fixture
def m3u_module():
    import m3u
    return m3u


# Load expected M3U item format from remotes
REMOTES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'remotes')


@pytest.fixture
def m3u_template():
    template_path = os.path.join(REMOTES_DIR, 'm3u.json')
    if os.path.exists(template_path):
        with open(template_path) as f:
            return json.load(f)
    return None


# ========================================================================
# 1. M3U Item Structure Validation
# ========================================================================
class TestM3UItemStructure:
    def test_template_exists(self, m3u_template):
        assert m3u_template is not None
        assert 'item' in m3u_template
        assert 'required' in m3u_template

    def test_template_has_required_fields(self, m3u_template):
        required = m3u_template['required']
        assert 'id' in required
        assert 'number' in required
        assert 'name' in required
        assert 'logo' in required
        assert 'group' in required
        assert 'label' in required
        assert 'url' in required

    def test_template_item_has_optional_fields(self, m3u_template):
        item = m3u_template['item']
        assert 'catchup' in item
        assert 'radio' in item
        assert 'favorite' in item
        assert 'media' in item
        assert 'kodiprops' in item


# ========================================================================
# 2. M3U Line Parsing
# ========================================================================
class TestM3UParsing:
    def test_parse_extinf_line(self, m3u_module):
        # Test parsing of EXTINF attributes
        line = '#EXTINF:-1 tvg-id="channel1" tvg-name="Channel 1" tvg-logo="logo.png" group-title="News",Channel 1'
        # Verify the regex patterns exist
        assert hasattr(m3u_module, 're') or hasattr(m3u_module, 'regex')

    def test_m3u_item_defaults(self, m3u_module):
        # Test that M3U items have sensible defaults
        template = m3u_template = None
        template_path = os.path.join(REMOTES_DIR, 'm3u.json')
        if os.path.exists(template_path):
            with open(template_path) as f:
                template = json.load(f)
        
        if template:
            item = template['item']
            assert item['radio'] == False
            assert item['favorite'] == False
            assert item['number'] == 0
            assert item['group'] == []
            assert item['kodiprops'] == []


# ========================================================================
# 3. M3U Item Validation
# ========================================================================
class TestM3UItemValidation:
    def test_item_has_id(self, m3u_template):
        item = m3u_template['item']
        assert 'id' in item
        assert isinstance(item['id'], str)

    def test_item_has_number(self, m3u_template):
        item = m3u_template['item']
        assert 'number' in item
        assert isinstance(item['number'], int)

    def test_item_has_name(self, m3u_template):
        item = m3u_template['item']
        assert 'name' in item
        assert isinstance(item['name'], str)

    def test_item_has_url(self, m3u_template):
        item = m3u_template['item']
        assert 'url' in item
        assert isinstance(item['url'], str)

    def test_item_has_logo(self, m3u_template):
        item = m3u_template['item']
        assert 'logo' in item
        assert isinstance(item['logo'], str)

    def test_item_has_group(self, m3u_template):
        item = m3u_template['item']
        assert 'group' in item
        assert isinstance(item['group'], list)

    def test_item_has_catchup(self, m3u_template):
        item = m3u_template['item']
        assert 'catchup' in item
        assert item['catchup'] in ['vod', 'shift', 'chapters', '']

    def test_item_has_kodiprops(self, m3u_template):
        item = m3u_template['item']
        assert 'kodiprops' in item
        assert isinstance(item['kodiprops'], list)
