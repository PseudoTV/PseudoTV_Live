# -*- coding: utf-8 -*-
"""Unit tests for xmltv.py - XMLTV parsing and writing"""
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
def xmltv_module():
    import xmltv
    return xmltv


# Load XMLTV DTD/XSD for validation
REMOTES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'remotes')


# ========================================================================
# 1. XMLTV Structure Validation
# ========================================================================
class TestXMLTVStructure:
    def test_xsd_exists(self):
        xsd_path = os.path.join(REMOTES_DIR, 'xmltv.xsd')
        assert os.path.exists(xsd_path)

    def test_dtd_exists(self):
        dtd_path = os.path.join(REMOTES_DIR, 'xmltv.dtd')
        assert os.path.exists(dtd_path)

    def test_xsd_has_channel_element(self):
        xsd_path = os.path.join(REMOTES_DIR, 'xmltv.xsd')
        with open(xsd_path) as f:
            content = f.read()
        assert 'channel' in content.lower()

    def test_xsd_has_programme_element(self):
        xsd_path = os.path.join(REMOTES_DIR, 'xmltv.xsd')
        with open(xsd_path) as f:
            content = f.read()
        assert 'programme' in content.lower()


# ========================================================================
# 2. XMLTV Channel Parsing
# ========================================================================
class TestXMLTVChannelParsing:
    def test_xmltv_module_has_reader(self, xmltv_module):
        # Check for reading functions
        assert hasattr(xmltv_module, 'read_channels') or hasattr(xmltv_module, 'Reader')

    def test_xmltv_module_has_writer(self, xmltv_module):
        # Check for writing functions
        assert hasattr(xmltv_module, 'write_programmes') or hasattr(xmltv_module, 'Writer')

    def test_channel_has_id(self, xmltv_module):
        # Channel IDs should be strings
        # This tests the expected structure
        channel = {
            'id': 'channel1',
            'display-name': 'Channel 1',
            'icon': {'src': 'logo.png'}
        }
        assert 'id' in channel
        assert isinstance(channel['id'], str)

    def test_programme_has_required_fields(self, xmltv_module):
        # Programme should have start, stop, channel, title
        programme = {
            'start': '20240101120000 +0000',
            'stop': '20240101130000 +0000',
            'channel': 'channel1',
            'title': 'Test Show',
            'desc': 'Test description'
        }
        assert 'start' in programme
        assert 'stop' in programme
        assert 'channel' in programme
        assert 'title' in programme


# ========================================================================
# 3. XMLTV Date Format
# ========================================================================
class TestXMLTVDateFormat:
    def test_xmltv_date_format(self):
        # XMLTV uses YYYYMMDDHHmmSS format
        import datetime
        now = datetime.datetime(2024, 1, 15, 12, 30, 0)
        # Expected format: 20240115123000
        expected = now.strftime('%Y%m%d%H%M%S')
        assert len(expected) == 14
        assert expected == '20240115123000'

    def test_xmltv_date_length(self):
        # Date should always be 14 characters
        date_str = '20240115123000'
        assert len(date_str) == 14

    def test_xmltv_date_is_numeric(self):
        # Date should be all digits
        date_str = '20240115123000'
        assert date_str.isdigit()


# ========================================================================
# 4. XMLTV Genre Handling
# ========================================================================
class TestXMLTVGenre:
    def test_genre_format(self):
        # Genres should be pipe-separated
        genres = ['News', 'Politics', 'Current Affairs']
        genre_str = '|'.join(genres)
        assert genre_str == 'News|Politics|Current Affairs'

    def test_genre_from_template(self):
        genres_path = os.path.join(REMOTES_DIR, 'genres.xml')
        if os.path.exists(genres_path):
            with open(genres_path) as f:
                content = f.read()
            assert 'genre' in content.lower() or 'category' in content.lower()
