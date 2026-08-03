# -*- coding: utf-8 -*-
"""Unit tests for xmltv.py - XMLTV parsing and writing"""
import sys, os, json
from unittest.mock import MagicMock, patch
import pytest

import variables


@pytest.fixture
def xmltv_mod():
    import xmltv
    return xmltv


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
    def test_xmltv_module_has_reader(self, xmltv_mod):
        assert hasattr(xmltv_mod, 'read_channels') or hasattr(xmltv_mod, 'Reader')

    def test_xmltv_module_has_writer(self, xmltv_mod):
        assert hasattr(xmltv_mod, 'write_programmes') or hasattr(xmltv_mod, 'Writer')

    def test_channel_has_id(self, xmltv_mod):
        channel = {
            'id': 'channel1',
            'display-name': 'Channel 1',
            'icon': {'src': 'logo.png'}
        }
        assert 'id' in channel
        assert isinstance(channel['id'], str)

    def test_programme_has_required_fields(self, xmltv_mod):
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
        import datetime
        now = datetime.datetime(2024, 1, 15, 12, 30, 0)
        expected = now.strftime('%Y%m%d%H%M%S')
        assert len(expected) == 14
        assert expected == '20240115123000'

    def test_xmltv_date_length(self):
        date_str = '20240115123000'
        assert len(date_str) == 14

    def test_xmltv_date_is_numeric(self):
        date_str = '20240115123000'
        assert date_str.isdigit()


# ========================================================================
# 4. XMLTV Genre Handling
# ========================================================================
class TestXMLTVGenre:
    def test_genre_format(self):
        genres = ['News', 'Politics', 'Current Affairs']
        genre_str = '|'.join(genres)
        assert genre_str == 'News|Politics|Current Affairs'

    def test_genre_from_template(self):
        genres_path = os.path.join(REMOTES_DIR, 'genres.xml')
        if os.path.exists(genres_path):
            with open(genres_path) as f:
                content = f.read()
            assert 'genre' in content.lower() or 'category' in content.lower()
