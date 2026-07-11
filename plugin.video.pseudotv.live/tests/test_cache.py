# -*- coding: utf-8 -*-
"""Unit tests for cache.py"""
import sys, os, datetime
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

# Import variables first to break circular import
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
def cache_module():
    from cache import _Cache
    return _Cache


# ========================================================================
# 1. getChecksum
# ========================================================================
class TestGetChecksum:
    def test_checksum_deterministic(self, cache_module):
        c = cache_module()
        r1 = c.getChecksum("test_data")
        r2 = c.getChecksum("test_data")
        assert r1 == r2

    def test_checksum_different_data(self, cache_module):
        c = cache_module()
        r1 = c.getChecksum("data1")
        r2 = c.getChecksum("data2")
        assert r1 != r2

    def test_checksum_returns_int(self, cache_module):
        c = cache_module()
        result = c.getChecksum("test")
        assert isinstance(result, int)


# ========================================================================
# 2. getTimestamp
# ========================================================================
class TestGetTimestamp:
    def test_returns_integer(self, cache_module):
        import datetime
        c = cache_module()
        now = datetime.datetime.now()
        result = c.getTimestamp(now)
        assert isinstance(result, int)

    def test_returns_current_time(self, cache_module):
        import datetime, time
        c = cache_module()
        now = datetime.datetime.now()
        before = int(time.time())
        result = c.getTimestamp(now)
        after = int(time.time())
        assert before <= result <= after + 1


# ========================================================================
# 3. getFreeMEM (now in constants.py)
# ========================================================================
class TestGetFreeMEM:
    def test_returns_numeric(self):
        from constants import _getFreeMEM
        result = _getFreeMEM()
        assert isinstance(result, (int, float))

    def test_returns_positive_value(self):
        from constants import _getFreeMEM
        result = _getFreeMEM()
        assert result > 0


# ========================================================================
# 4. cacheit decorator
# ========================================================================
class TestCacheitDecorator:
    def test_decorator_exists(self):
        from cache import cacheit
        assert callable(cacheit)

    def test_decorator_returns_callable(self):
        from cache import cacheit
        import datetime
        decorator = cacheit(expiration=datetime.timedelta(seconds=60))
        assert callable(decorator)

    def test_decorator_wraps_function(self):
        from cache import cacheit
        import datetime
        
        @cacheit(expiration=datetime.timedelta(seconds=60))
        def test_func(x):
            return x * 2
        
        # The wrapper should exist
        assert hasattr(test_func, '__wrapped__') or callable(test_func)


# ========================================================================
# 5. Cache class public API
# ========================================================================
class TestCacheClass:
    def test_cache_exists(self):
        from cache import Cache
        assert callable(Cache)

    def test_cache_has_clear_method(self):
        from cache import Cache
        assert hasattr(Cache, 'clear')

    def test_cache_has_checkpoint_method(self):
        from cache import Cache
        assert hasattr(Cache, 'checkpoint')

    def test_cache_has_shutdown_method(self):
        from cache import Cache
        assert hasattr(Cache, 'shutdown')

    def test_cache_has_set_method(self):
        from cache import Cache
        assert hasattr(Cache, 'set')

    def test_cache_has_get_method(self):
        from cache import Cache
        assert hasattr(Cache, 'get')
