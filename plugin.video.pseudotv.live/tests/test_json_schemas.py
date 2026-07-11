# -*- coding: utf-8 -*-
"""JSON schema validation tests using remotes/ templates"""
import sys, os, json
import pytest

REMOTES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'remotes')


# ========================================================================
# 1. channels.json Schema Validation
# ========================================================================
class TestChannelsSchema:
    @pytest.fixture
    def channels_template(self):
        path = os.path.join(REMOTES_DIR, 'channels.json')
        with open(path) as f:
            return json.load(f)

    def test_has_version(self, channels_template):
        assert 'version' in channels_template
        assert isinstance(channels_template['version'], str)

    def test_has_uuid(self, channels_template):
        assert 'uuid' in channels_template

    def test_has_channels_array(self, channels_template):
        assert 'channels' in channels_template
        assert isinstance(channels_template['channels'], list)

    def test_channel_has_required_fields(self, channels_template):
        channel = channels_template['channels'][0]
        required = ['id', 'type', 'number', 'name', 'logo', 'path', 'group', 'rules']
        for field in required:
            assert field in channel, f"Missing field: {field}"

    def test_channel_has_boolean_fields(self, channels_template):
        channel = channels_template['channels'][0]
        assert 'radio' in channel
        assert isinstance(channel['radio'], bool)
        assert 'favorite' in channel
        assert isinstance(channel['favorite'], bool)
        assert 'enable' in channel
        assert isinstance(channel['enable'], bool)

    def test_channel_has_catchup(self, channels_template):
        channel = channels_template['channels'][0]
        assert 'catchup' in channel
        assert channel['catchup'] in ['vod', 'shift', 'chapters', '']

    def test_channel_rules_structure(self, channels_template):
        rules = channels_template['channels'][0]['rules']
        assert 'version' in rules
        assert isinstance(rules['version'], float)

    def test_has_plugins_array(self, channels_template):
        assert 'plugins' in channels_template
        assert isinstance(channels_template['plugins'], list)

    def test_plugin_has_vod_and_live(self, channels_template):
        plugin = channels_template['plugins'][0]
        assert 'vod' in plugin
        assert 'live' in plugin
        assert isinstance(plugin['vod'], list)
        assert isinstance(plugin['live'], list)


# ========================================================================
# 2. library.json Schema Validation
# ========================================================================
class TestLibrarySchema:
    @pytest.fixture
    def library_template(self):
        path = os.path.join(REMOTES_DIR, 'library.json')
        with open(path) as f:
            return json.load(f)

    def test_has_version(self, library_template):
        assert 'version' in library_template

    def test_has_library_object(self, library_template):
        assert 'library' in library_template
        assert isinstance(library_template['library'], dict)

    def test_library_has_categories(self, library_template):
        library = library_template['library']
        categories = [
            'TV Networks', 'TV Shows', 'TV Genres', 'Movie Genres',
            'Movie Studios', 'Mixed Genres', 'Mixed', 'Playlists',
            'Recommended', 'Services', 'Music Genres'
        ]
        for cat in categories:
            assert cat in library, f"Missing category: {cat}"

    def test_library_item_structure(self, library_template):
        item = library_template['library']['Item']
        assert 'type' in item
        assert 'name' in item
        assert 'logo' in item
        assert 'path' in item
        assert 'rules' in item

    def test_has_whitelist_and_blacklist(self, library_template):
        assert 'whitelist' in library_template
        assert isinstance(library_template['whitelist'], list)
        assert 'blacklist' in library_template
        assert isinstance(library_template['blacklist'], list)


# ========================================================================
# 3. m3u.json Schema Validation
# ========================================================================
class TestM3USchema:
    @pytest.fixture
    def m3u_template(self):
        path = os.path.join(REMOTES_DIR, 'm3u.json')
        with open(path) as f:
            return json.load(f)

    def test_has_item(self, m3u_template):
        assert 'item' in m3u_template

    def test_has_required(self, m3u_template):
        assert 'required' in m3u_template

    def test_item_has_all_fields(self, m3u_template):
        item = m3u_template['item']
        fields = [
            'id', 'number', 'name', 'logo', 'group', 'catchup',
            'radio', 'favorite', 'realtime', 'media', 'label', 'url',
            'tvg-shift', 'x-tvg-url', 'media-dir', 'media-size', 'media-type',
            'catchup-source', 'catchup-days', 'catchup-correction',
            'provider', 'provider-type', 'provider-logo',
            'provider-countries', 'provider-languages',
            'x-playlist-type', 'kodiprops'
        ]
        for field in fields:
            assert field in item, f"Missing field: {field}"

    def test_required_fields_subset(self, m3u_template):
        required = m3u_template['required']
        item = m3u_template['item']
        for field in required:
            assert field in item, f"Required field missing in item: {field}"

    def test_item_types(self, m3u_template):
        item = m3u_template['item']
        assert isinstance(item['id'], str)
        assert isinstance(item['number'], int)
        assert isinstance(item['name'], str)
        assert isinstance(item['logo'], str)
        assert isinstance(item['group'], list)
        assert isinstance(item['radio'], bool)
        assert isinstance(item['favorite'], bool)
        assert isinstance(item['kodiprops'], list)


# ========================================================================
# 4. servers.json Schema Validation
# ========================================================================
class TestServersSchema:
    @pytest.fixture
    def servers_template(self):
        path = os.path.join(REMOTES_DIR, 'servers.json')
        with open(path) as f:
            return json.load(f)

    def test_has_version(self, servers_template):
        assert 'version' in servers_template

    def test_has_servers_object(self, servers_template):
        assert 'servers' in servers_template

    def test_server_has_required_fields(self, servers_template):
        server = servers_template['servers']['friendly']
        required = ['id', 'version', 'uuid', 'name', 'host', 'remotes', 'settings', 'enabled', 'online', 'updated']
        for field in required:
            assert field in server, f"Missing field: {field}"

    def test_server_boolean_fields(self, servers_template):
        server = servers_template['servers']['friendly']
        assert isinstance(server['enabled'], bool)
        assert isinstance(server['online'], bool)

    def test_server_has_nested_objects(self, servers_template):
        server = servers_template['servers']['friendly']
        assert isinstance(server['remotes'], dict)
        assert isinstance(server['settings'], dict)


# ========================================================================
# 5. holidays.json Schema Validation
# ========================================================================
class TestHolidaysSchema:
    @pytest.fixture
    def holidays_template(self):
        path = os.path.join(REMOTES_DIR, 'holidays.json')
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    def test_file_exists(self):
        path = os.path.join(REMOTES_DIR, 'holidays.json')
        assert os.path.exists(path)

    def test_is_valid_json(self, holidays_template):
        assert holidays_template is not None

    def test_has_holiday_structure(self, holidays_template):
        # Holidays should be a list or dict
        assert isinstance(holidays_template, (list, dict))


# ========================================================================
# 6. seasons.json Schema Validation
# ========================================================================
class TestSeasonsSchema:
    @pytest.fixture
    def seasons_template(self):
        path = os.path.join(REMOTES_DIR, 'seasons.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        return None

    def test_file_exists(self):
        path = os.path.join(REMOTES_DIR, 'seasons.json')
        assert os.path.exists(path)

    def test_is_valid_json(self, seasons_template):
        assert seasons_template is not None

    def test_has_months(self, seasons_template):
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']
        for month in months:
            assert month in seasons_template, f"Missing month: {month}"

    def test_month_has_days(self, seasons_template):
        # Each month should have days as keys
        january = seasons_template['January']
        assert '1' in january
        assert '31' in january

    def test_day_has_structure(self, seasons_template):
        # Each day should have name, tagline, keyword, logo
        jan_1 = seasons_template['January']['1']
        assert 'name' in jan_1
        assert 'tagline' in jan_1
        assert 'keyword' in jan_1
        assert 'logo' in jan_1
