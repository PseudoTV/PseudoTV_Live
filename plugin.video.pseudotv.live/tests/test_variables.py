# -*- coding: utf-8 -*-
"""Unit tests for variables.py"""
import sys, os, re, math, time as _time, datetime, random, urllib.parse
from collections import OrderedDict
from unittest.mock import MagicMock, patch
import pytest

import variables


@pytest.fixture
def globals_class():
    from variables import Globals
    return Globals

# ========================================================================
# 1. _parseSE - Season/Episode parsing
# ========================================================================

class TestParseSE:
    @pytest.mark.parametrize('filename, expected', [
        ('Show.Name.S01E05.720p.mkv', (1, 5)),
        ('Show Name - Season 2 Episode 3.mkv', (2, 3)),
        ('show.name.s01e12.hdtv.mp4', (1, 12)),
        ('MyShow - S10E99.mkv', (10, 99)),
        ('s01e01.mkv', (1, 1)),
        ('S2E10.mkv', (2, 10)),
        ('Show.Name.1x05.mkv', (1, 5)),
        ('Show.Name.10x01.mkv', (10, 1)),
    ])
    def test_parse_se_valid(self, globals_class, filename, expected):
        assert globals_class._parseSE(filename) == expected

    @pytest.mark.parametrize('filename, expected', [
        ('movie.mp4', (-1, -1)),
        ('Random.File.Name', (-1, -1)),
        ('', (-1, -1)),
    ])
    def test_parse_se_no_match(self, globals_class, filename, expected):
        assert globals_class._parseSE(filename) == expected

    def test_parse_se_edge_case_zero(self, globals_class):
        assert globals_class._parseSE('Show.S00E00.mkv') == (0, 0)


# ========================================================================
# 2. _splitYear / _stripRegion
# ========================================================================

class TestSplitYear:
    @pytest.mark.parametrize('label, exp_label, exp_year', [
        ('Movie (2020)', 'Movie', 2020),
        ('Show Name (1999)', 'Show Name', 1999),
        ('No year here', 'No year here', None),
        ('', '', None),
        ('Movie (ABCD)', 'Movie', None),
    ])
    def test_split_year(self, globals_class, label, exp_label, exp_year):
        result_label, result_year = globals_class._splitYear(label)
        assert result_label == exp_label
        assert result_year == exp_year


class TestStripRegion:
    @pytest.mark.parametrize('label, expected', [
        ('Movie (2020)', 'Movie'),
        ('Show Name (1999)', 'Show Name'),
        ('No year here', 'No year here'),
    ])
    def test_strip_region(self, globals_class, label, expected):
        assert globals_class._stripRegion(label) == expected


# ========================================================================
# 3. _slugify
# ========================================================================

class TestSlugify:
    @pytest.mark.parametrize('input_str, lowercase, expected', [
        ('Hello World', False, 'Hello_World'),
        ('Hello World', True, 'hello_world'),
        ('  spaces  ', False, 'spaces'),
        ('--leading-trailing--', False, '_leading_trailing_'),
        ('Special!@#Chars', False, 'SpecialChars'),
        ('', False, ''),
    ])
    def test_slugify(self, globals_class, input_str, lowercase, expected):
        assert globals_class._slugify(input_str, lowercase) == expected


# ========================================================================
# 4. _getAbbr
# ========================================================================

class TestGetAbbr:
    def test_two_word(self, globals_class):
        assert globals_class._getAbbr('Hello World') == 'H.W.'
    def test_single_word(self, globals_class):
        assert globals_class._getAbbr('Test') == 'T'
    def test_three_words(self, globals_class):
        assert globals_class._getAbbr('A B C') == 'A.B.'


# ========================================================================
# 5. _escapeString / _unescapeString
# ========================================================================

class TestEscapeString:
    def test_escape_ampersand(self, globals_class):
        result = globals_class._escapeString('A & B')
        assert '&amp;' in result
    def test_roundtrip(self, globals_class):
        original = 'He said hello & goodbye <world>'
        escaped = globals_class._escapeString(original)
        unescaped = globals_class._unescapeString(escaped)
        assert unescaped == original


# ========================================================================
# 6. _hasURLencoding
# ========================================================================

class TestHasURLEncoding:
    @pytest.mark.parametrize('text, expected', [
        ('hello%20world', True),
        ('path/to/file', False),
        ('100%', False),
        ('abc%FFdef', True),
    ])
    def test_has_url_encoding(self, globals_class, text, expected):
        assert globals_class._hasURLencoding(text) == expected


# ========================================================================
# 7. ratings.local - rating cleanup (moved from Globals._cleanMPAA to ratings.py)
# ========================================================================

class TestCleanMPAA:
    @pytest.mark.parametrize('mpaa, expected', [
        ('Rated PG-13', 'PG-13'),
        ('rated R', 'R'),
        ('US:PG', 'PG'),
        ('PG-13 / US', 'PG-13'),
        ('PG', 'PG'),
        ('', ''),
    ])
    def test_clean_mpaa(self, mpaa, expected):
        from ratings import local
        assert local(mpaa) == expected


# ========================================================================
# 8. _percentDiff
# ========================================================================

class TestPercentDiff:
    def test_same_values(self, globals_class):
        assert globals_class._percentDiff(100.0, 100.0) == 0.0
    def test_different_values(self, globals_class):
        result = globals_class._percentDiff(100.0, 50.0)
        assert result == pytest.approx(100.0, abs=0.1)
    def test_zero_division(self, globals_class):
        assert globals_class._percentDiff(100.0, 0.0) == -1


# ========================================================================
# 9. _timeString2Seconds
# ========================================================================

class TestTimeString2Seconds:
    @pytest.mark.parametrize('time_str, expected', [
        ('00:00:00', 0),
        ('00:01:00', 60),
        ('01:00:00', 3600),
        ('01:30:00', 5400),
        ('10:30:15', 37815),
    ])
    def test_valid_times(self, globals_class, time_str, expected):
        assert globals_class._timeString2Seconds(time_str) == expected
    def test_invalid_string(self, globals_class):
        assert globals_class._timeString2Seconds('invalid') == -1
    def test_empty_string(self, globals_class):
        assert globals_class._timeString2Seconds('') == -1


# ========================================================================
# 10. _chunkLst / _pagination
# ========================================================================

class TestChunkLst:
    def test_even_split(self, globals_class):
        result = list(globals_class._chunkLst([1, 2, 3, 4], 2))
        assert result == [[1, 2], [3, 4]]
    def test_uneven_split(self, globals_class):
        result = list(globals_class._chunkLst([1, 2, 3, 4, 5], 2))
        assert result == [[1, 2], [3, 4], [5]]
    def test_empty_list(self, globals_class):
        result = list(globals_class._chunkLst([], 3))
        assert result == []


class TestPagination:
    def test_pagination(self, globals_class):
        result = list(globals_class._pagination([1, 2, 3, 4, 5], 2))
        assert result == [[1, 2], [3, 4], [5]]


# ========================================================================
# 11. _interleave
# ========================================================================

class TestInterleave:
    def test_sets_zero_concatenates(self, globals_class):
        result = globals_class._interleave([[1, 2], ['a', 'b']], sets=0)
        assert result == [1, 2, 'a', 'b']
    def test_sets_one(self, globals_class):
        result = globals_class._interleave([[1, 2, 3], ['a', 'b', 'c']], sets=1)
        assert result[0] == 1
        assert result[1] == 'a'
    def test_empty_lists(self, globals_class):
        result = globals_class._interleave([[], []], sets=1)
        assert result == []


# ========================================================================
# 12. _randomShuffle / _randomSamples
# ========================================================================

class TestRandomShuffle:
    def test_shuffle_preserves_elements(self, globals_class):
        items = [1, 2, 3, 4, 5]
        result = globals_class._randomShuffle(items)
        assert sorted(result) == sorted(items)
    def test_shuffle_preserves_type(self, globals_class):
        items = (1, 2, 3)
        result = globals_class._randomShuffle(items)
        assert isinstance(result, tuple)
        assert sorted(result) == sorted(items)
    def test_shuffle_dict(self, globals_class):
        items = {'a': 1, 'b': 2, 'c': 3}
        result = globals_class._randomShuffle(items)
        assert isinstance(result, dict)
        assert set(result.keys()) == set(items.keys())
        assert set(result.values()) == set(items.values())
    def test_shuffle_empty(self, globals_class):
        assert globals_class._randomShuffle([]) == []
        assert globals_class._randomShuffle(()) == ()
    def test_shuffle_non_collection(self, globals_class):
        assert globals_class._randomShuffle(42) == 42
        assert globals_class._randomShuffle('hello') == 'hello'


class TestRandomSamples:
    def test_sample_all(self, globals_class):
        items = [1, 2, 3, 4, 5]
        result = globals_class._randomSamples(items, -1)
        assert sorted(result) == sorted(items)
    def test_sample_subset(self, globals_class):
        items = [1, 2, 3, 4, 5]
        result = globals_class._randomSamples(items, 3)
        assert len(result) == 3
        assert all(x in items for x in result)
    def test_sample_none(self, globals_class):
        assert globals_class._randomSamples(None) == []


# ========================================================================
# 13. _isStack / _splitStacks
# ========================================================================

class TestStackedFiles:
    def test_is_stack_true(self, globals_class):
        assert globals_class._isStack('stack://file1.mkv , file2.mkv') is True
    def test_is_stack_false(self, globals_class):
        assert globals_class._isStack('regular/file.mkv') is False
    def test_split_stacks(self, globals_class):
        path = 'stack://part1.mkv , part2.mkv'
        result = globals_class._splitStacks(path)
        assert result == ['part1.mkv', 'part2.mkv']
    def test_split_stacks_non_stack(self, globals_class):
        path = 'regular/file.mkv'
        result = globals_class._splitStacks(path)
        assert result == ['regular/file.mkv']


# ========================================================================
# 14. _isFiller
# ========================================================================

class TestIsFiller:
    def test_is_filler_by_genre(self, globals_class):
        item = {'genre': ['Fillers', 'Comedy']}
        assert globals_class._isFiller(item) is True
    def test_is_not_filler(self, globals_class):
        item = {'genre': ['Action', 'Drama']}
        assert globals_class._isFiller(item) is False
    def test_empty_genre(self, globals_class):
        item = {'genre': []}
        assert globals_class._isFiller(item) is False
    def test_no_genre(self, globals_class):
        item = {}
        assert globals_class._isFiller(item) is False


# ========================================================================
# 15. _getLabel
# ========================================================================

class TestGetLabel:
    def test_label_from_name(self, globals_class):
        item = {'name': 'Test Movie'}
        assert globals_class._getLabel(item) == 'Test Movie'
    def test_label_from_label(self, globals_class):
        item = {'label': 'Test Show'}
        assert globals_class._getLabel(item) == 'Test Show'
    def test_label_empty_item(self, globals_class):
        item = {}
        assert globals_class._getLabel(item) == ''


# ========================================================================
# 16. _roundupDIV
# ========================================================================

class TestRoundupDIV:
    def test_exact_division(self, globals_class):
        assert globals_class._roundupDIV(10, 2) == 5
    def test_roundup_needed(self, globals_class):
        assert globals_class._roundupDIV(10, 3) == 4
    def test_zero_division(self, globals_class):
        assert globals_class._roundupDIV(10, 0) == 1


# ========================================================================
# 17. _combineDicts
# ========================================================================

class TestCombineDicts:
    def test_combine_basic(self, globals_class):
        d1 = {'a': 1, 'b': 2}
        d2 = {'c': 3, 'd': 4}
        result = globals_class._combineDicts(d1, d2)
        assert result == {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    def test_combine_overlap(self, globals_class):
        d1 = {'a': 1}
        d2 = {'a': 2}
        result = globals_class._combineDicts(d1, d2)
        assert result == {'a': 2}


# ========================================================================
# 18. _cleanLabel
# ========================================================================

class TestCleanLabel:
    def test_remove_color_tags(self, globals_class):
        text = '[COLOR=red]Hello[/COLOR]'
        result = globals_class._cleanLabel(text)
        assert 'Hello' in result
        assert '[COLOR' not in result
    def test_remove_bold_tags(self, globals_class):
        text = '[B]Bold[/B]'
        result = globals_class._cleanLabel(text)
        assert 'Bold' in result
        assert '[B]' not in result
    def test_remove_colon(self, globals_class):
        text = 'Show: Episode'
        result = globals_class._cleanLabel(text)
        assert ':' not in result
    def test_plain_text(self, globals_class):
        text = 'Plain text'
        assert globals_class._cleanLabel(text) == 'Plain text'


# ========================================================================
# 19. _stripNumber
# ========================================================================

class TestStripNumber:
    def test_strip_numbers(self, globals_class):
        assert globals_class._stripNumber('abc123def') == 'abcdef'
    def test_no_numbers(self, globals_class):
        assert globals_class._stripNumber('abc') == 'abc'
    def test_all_numbers(self, globals_class):
        assert globals_class._stripNumber('12345') == ''


# ========================================================================
# 20. _encodePlot / _decodePlot
# ========================================================================

class TestEncodeDecodePlot:
    def test_encode_decode_roundtrip(self, globals_class):
        plot = 'Original plot text'
        metadata = {'key': 'value', 'number': 42}
        encoded = globals_class._encodePlot(plot, metadata)
        assert plot in encoded
        assert '[COLOR item=' in encoded
        decoded = globals_class._decodePlot(encoded)
        assert decoded.get('key') == 'value'
        assert decoded.get('number') == 42
    def test_decode_empty_string(self, globals_class):
        assert globals_class._decodePlot('') == {}
    def test_decode_no_metadata(self, globals_class):
        assert globals_class._decodePlot('No metadata here') == {}
    def test_decode_non_string(self, globals_class):
        assert globals_class._decodePlot(None) == {}


# ========================================================================
# 21. _getChannelID / _getRecordID
# ========================================================================

class TestChannelID:
    def test_channel_id_deterministic(self, globals_class):
        with patch('variables.ADDON_NAME', 'PseudoTV Live'):
            id1 = globals_class._getChannelID('Test', 'path', 1, 'uuid123')
            id2 = globals_class._getChannelID('Test', 'path', 1, 'uuid123')
            assert id1 == id2

    def test_channel_id_format(self, globals_class):
        with patch('variables.ADDON_NAME', 'PseudoTV Live'):
            result = globals_class._getChannelID('Test', 'path', 1, 'uuid123')
            assert '@' in result
            parts = result.split('@')
            assert len(parts[0]) == 32
            assert parts[1] == 'PseudoTV_Live'

    def test_record_id_shorter(self, globals_class):
        with patch('variables.ADDON_NAME', 'PseudoTV Live'):
            ch_id = globals_class._getChannelID('Test', 'path', 1, 'uuid123')
            rec_id = globals_class._getRecordID('Test', 'path', 1, 'uuid123')
            assert len(rec_id) < len(ch_id)

    def test_different_paths_same_id_known_issue(self, globals_class):
        with patch('variables.ADDON_NAME', 'PseudoTV Live'):
            id1 = globals_class._getChannelID('Test', 'path1', 1, 'uuid')
            id2 = globals_class._getChannelID('Test', 'path2', 1, 'uuid')
            assert id1 == id2

    def test_list_path_handling(self, globals_class):
        with patch('variables.ADDON_NAME', 'PseudoTV Live'):
            id1 = globals_class._getChannelID('Test', ['a', 'b'], 1, 'uuid')
            id2 = globals_class._getChannelID('Test', 'a|b', 1, 'uuid')
            assert id1 == id2

    def test_uuid_not_in_id_due_to_hash_object(self, globals_class):
        with patch('variables.ADDON_NAME', 'PseudoTV Live'):
            id1 = globals_class._getChannelID('Test', 'path', 1, 'uuid1')
            id2 = globals_class._getChannelID('Test', 'path', 1, 'uuid2')
            assert id1 == id2

    def test_number_affects_id(self, globals_class):
        with patch('variables.ADDON_NAME', 'PseudoTV Live'):
            id1 = globals_class._getChannelID('Test', 'path', 1, 'uuid')
            id2 = globals_class._getChannelID('Test', 'path', 2, 'uuid')
            assert id1 != id2


# ========================================================================
# 22. _mergeDict
# ========================================================================

class TestMergeDict:
    def test_merge_basic(self, globals_class):
        d1 = [{'label': 'a'}, {'label': 'b'}]
        d2 = [{'label': 'c'}]
        result = globals_class._mergeDict(d1, d2)
        assert len(result) == 3
    def test_merge_dedup(self, globals_class):
        d1 = [{'label': 'a'}]
        d2 = [{'label': 'a'}, {'label': 'b'}]
        result = globals_class._mergeDict(d1, d2)
        assert len(result) == 2


# ========================================================================
# 23. _compareDict
# ========================================================================

class TestCompareDict:
    def test_same_dicts(self, globals_class):
        d1 = [{'name': 'b'}, {'name': 'a'}]
        d2 = [{'name': 'a'}, {'name': 'b'}]
        assert globals_class._compareDict(d1, d2, 'name') is True
    def test_different_dicts(self, globals_class):
        d1 = [{'name': 'a'}]
        d2 = [{'name': 'b'}]
        assert globals_class._compareDict(d1, d2, 'name') is False


# ========================================================================
# 24. _isRadio
# ========================================================================

class TestIsRadio:
    def test_radio_flag_true(self, globals_class):
        item = {'radio': True}
        assert globals_class._isRadio(item) is True
    def test_music_genre(self, globals_class):
        item = {'type': 'Music Genres'}
        assert globals_class._isRadio(item) is True
    def test_music_path(self, globals_class):
        item = {'path': ['musicdb://artists/']}
        assert globals_class._isRadio(item) is True
    def test_not_radio(self, globals_class):
        item = {'path': ['videodb://movies/']}
        assert globals_class._isRadio(item) is False


# ========================================================================
# 25. _chkLogo
# ========================================================================

class TestChkLogo:
    def test_keep_existing_if_new_is_wlogo(self, globals_class):
        old = '/path/to/logo.png'
        new = '/path/to/wlogo.png'
        assert globals_class._chkLogo(old, new) == old
    def test_use_new_if_not_wlogo(self, globals_class):
        old = '/path/to/logo.png'
        new = '/path/to/channel_logo.png'
        assert globals_class._chkLogo(old, new) == new


# ========================================================================
# 26. _escapeDirJSON
# ========================================================================

class TestEscapeDirJSON:
    def test_no_colon(self, globals_class):
        path = '/unix/path'
        result = globals_class._escapeDirJSON(path)
        assert result == path


# ========================================================================
# 27. _frange
# ========================================================================

class TestFrange:
    def test_basic_frange(self, globals_class):
        result = globals_class._frange(0, 10, 2)
        assert result == [0.0, 0.2, 0.4, 0.6, 0.8]


# ========================================================================
# 28. _subZoom / _addZoom
# ========================================================================

class TestZoomCalculations:
    def test_sub_zoom(self, globals_class):
        result = globals_class._subZoom(100, 0.5)
        assert result == 50
    def test_add_zoom(self, globals_class):
        result = globals_class._addZoom(100, 0.5)
        assert result == 150


# ========================================================================
# 29. _roundTimeDown / _roundTimeUp
# ========================================================================

class TestTimeRounding:
    def test_round_down_30min(self, globals_class):
        dt = 1672531200.0
        result = globals_class._roundTimeDown(dt, 30)
        assert result % 1800 == 0
    def test_round_up_60min(self, globals_class):
        dt = 1672531200.0
        result = globals_class._roundTimeUp(dt, 60)
        assert result % 3600 == 0


# ========================================================================
# 30. double_urlencode / single_urlencode
# ========================================================================

class TestURLEncoding:
    def test_single_urlencode(self, globals_class):
        result = globals_class.single_urlencode('hello world')
        assert 'hello' in result
        assert 'world' in result
    def test_double_urlencode(self, globals_class):
        result = globals_class.double_urlencode('hello world')
        single = globals_class.single_urlencode('hello world')
        assert len(result) >= len(single)


# ========================================================================
# 31. diffLSTDICT
# ========================================================================

class TestDiffLSTDICT:
    def test_same_lists(self, globals_class):
        old = [{'name': 'a'}, {'name': 'b'}]
        new = [{'name': 'a'}, {'name': 'b'}]
        result = globals_class.diffLSTDICT(old, new)
        assert len(result['added']) == 0
        assert len(result['removed']) == 0
    def test_additions(self, globals_class):
        old = [{'name': 'a'}]
        new = [{'name': 'a'}, {'name': 'b'}]
        result = globals_class.diffLSTDICT(old, new)
        assert len(result['added']) == 1
        assert len(result['removed']) == 0
    def test_removals(self, globals_class):
        old = [{'name': 'a'}, {'name': 'b'}]
        new = [{'name': 'a'}]
        result = globals_class.diffLSTDICT(old, new)
        assert len(result['added']) == 0
        assert len(result['removed']) == 1


# ========================================================================
# 32. _chunkDict
# ========================================================================

class TestChunkDict:
    def test_chunk_dict_basic(self, globals_class):
        items = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}
        result = list(globals_class._chunkDict(items, 2))
        assert len(result) == 3
        assert len(result[0]) == 2
        assert len(result[1]) == 2
        assert len(result[2]) == 1

    def test_chunk_dict_empty(self, globals_class):
        result = list(globals_class._chunkDict({}, 2))
        assert result == []

    def test_chunk_dict_single_chunk(self, globals_class):
        items = {'a': 1, 'b': 2}
        result = list(globals_class._chunkDict(items, 5))
        assert len(result) == 1
        assert len(result[0]) == 2


# ========================================================================
# 33. _isShort
# ========================================================================

class TestIsShort:
    def test_is_short_true(self, globals_class):
        with patch.object(globals_class.settings, 'getSettingInt', return_value=300):
            assert globals_class._isShort({'duration': 120}) == True

    def test_is_short_false(self, globals_class):
        with patch.object(globals_class.settings, 'getSettingInt', return_value=300):
            assert globals_class._isShort({'duration': 600}) == False

    def test_is_short_custom_min(self, globals_class):
        assert globals_class._isShort({'duration': 120}, minDuration=60) == False


# ========================================================================
# 34. _isEnding
# ========================================================================

class TestIsEnding:
    def test_is_ending_true(self, globals_class):
        with patch.object(globals_class.settings, 'getSettingInt', return_value=90):
            assert globals_class._isEnding(95) == True

    def test_is_ending_false(self, globals_class):
        with patch.object(globals_class.settings, 'getSettingInt', return_value=90):
            assert globals_class._isEnding(50) == False


# ========================================================================
# 35. _cleanImage
# ========================================================================

class TestCleanImage:
    def test_clean_image_strips_trailing_slash(self, globals_class):
        result = globals_class._cleanImage('https://example.com/logo.png/')
        assert result == 'https://example.com/logo.png'

    def test_clean_image_no_prefix(self, globals_class):
        result = globals_class._cleanImage('https://example.com/logo.png')
        assert result == 'https://example.com/logo.png'

    def test_clean_image_image_prefix(self, globals_class):
        result = globals_class._cleanImage('image://https://example.com/logo.png')
        assert result == 'image://https://example.com/logo.png'


# ========================================================================
# 36. _cleanGroups
# ========================================================================

class TestCleanGroups:
    def test_clean_groups_adds_addon_name(self, globals_class):
        with patch('variables.ADDON_NAME', 'PseudoTV Live'):
            citem = {'group': ['Movies', 'Action']}
            result = globals_class._cleanGroups(citem)
            assert 'PseudoTV Live' in result['group']

    def test_clean_groups_disabled_sets_default(self, globals_class):
        with patch('variables.ADDON_NAME', 'PseudoTV Live'), \
             patch.object(globals_class.settings, 'getSetting', return_value='false'):
            citem = {'group': ['Movies', 'Action']}
            result = globals_class._cleanGroups(citem)
            assert result['group'] == ['PseudoTV Live']

# ========================================================================
# 37. _openSettings focus offsets
# ========================================================================

class TestOpenSettingsFocus:
    def test_open_settings_uses_correct_control_ids(self, globals_class):
        """SetFocus must target the settings window's real controls: category
        grouplist id=3 and settings grouplist id=5 (per SettingsCategory.xml),
        using 0-based subitem indices — NOT the old negative ctl-200/ctl-180."""
        calls = []
        def fake_builtin(cmd):
            calls.append(cmd)
        with patch('variables.xbmc.executebuiltin', side_effect=fake_builtin), \
             patch('variables.xbmc.sleep'):
            globals_class._openSettings((5, 7))
        focus_calls = [c for c in calls if c.startswith('SetFocus(')]
        assert focus_calls == ['SetFocus(3, 5, absolute)', 'SetFocus(5, 7, absolute)']

    def test_open_settings_default_focus_channels(self, globals_class):
        """Default (0,1) focuses the channels category's first setting."""
        calls = []
        with patch('variables.xbmc.executebuiltin', side_effect=calls.append), \
             patch('variables.xbmc.sleep'):
            globals_class._openSettings()
        focus_calls = [c for c in calls if c.startswith('SetFocus(')]
        assert focus_calls == ['SetFocus(3, 0, absolute)', 'SetFocus(5, 1, absolute)']


# ========================================================================
# _toWebImage - rewrite SMB/VFS artwork to self-hosted /image/ URL
# ========================================================================

class TestToWebImage:
    """Raw smb:///nfs:// artwork in the served M3U/XMLTV made Kodi's image
    loader open SMB directly, racing Kodi's Samba idle-close and crashing
    libsmbclient. _toWebImage rewrites VFS paths to the /image/ endpoint."""

    def _make(self, globals_class):
        from variables import Globals
        # remote host is read from Globals.properties
        props = MagicMock()
        props.getEXTProperty.return_value = '192.168.0.53:50001'
        return globals_class, props

    def test_smb_rewritten_to_image_url(self, globals_class):
        from variables import Globals
        with patch('variables.Globals.properties.getEXTProperty', return_value='192.168.0.53:50001'):
            out = Globals._toWebImage('smb://USERNAME:PASSWORD@192.168.0.51/TV/Show/clearlogo.png')
        assert out.startswith('http://192.168.0.53:50001/image/')
        # decoded inner path must be the SMB path (forward slashes)
        import urllib.parse
        decoded = urllib.parse.unquote(out.split('/image/')[1])
        assert decoded == 'smb://USERNAME:PASSWORD@192.168.0.51/TV/Show/clearlogo.png'

    def test_http_passes_through(self, globals_class):
        from variables import Globals
        out = Globals._toWebImage('http://example.com/logo.png')
        assert out == 'http://example.com/logo.png'

    def test_empty_returns_empty(self, globals_class):
        from variables import Globals
        assert Globals._toWebImage('') == ''
        assert Globals._toWebImage(None) == ''
