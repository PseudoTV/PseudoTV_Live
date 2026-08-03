# -*- coding: utf-8 -*-
"""Unit tests for fileaccess.py"""
import sys, os, json, hashlib, zlib, base64, pickle
from collections import OrderedDict
from unittest.mock import MagicMock, patch
import pytest

import variables


@pytest.fixture
def fileaccess():
    from fileaccess import FileAccess
    return FileAccess


# ========================================================================
# 1. _getMD5
# ========================================================================
class TestGetMD5:
    def test_string_input(self, fileaccess):
        result = fileaccess._getMD5("hello")
        expected = hashlib.md5("hello".encode("utf-8")).hexdigest()
        assert result == expected

    def test_bytes_input(self, fileaccess):
        result = fileaccess._getMD5(b"hello")
        expected = hashlib.md5(b"hello").hexdigest()
        assert result == expected

    def test_dict_input(self, fileaccess):
        data = {"key": "value"}
        result = fileaccess._getMD5(data)
        assert isinstance(result, str)
        assert len(result) == 32

    def test_deterministic(self, fileaccess):
        r1 = fileaccess._getMD5("test")
        r2 = fileaccess._getMD5("test")
        assert r1 == r2

    def test_different_inputs_different_hash(self, fileaccess):
        r1 = fileaccess._getMD5("abc")
        r2 = fileaccess._getMD5("xyz")
        assert r1 != r2


# ========================================================================
# 2. _encodeString / _decodeString roundtrip
# ========================================================================
class TestEncodeDecodeString:
    def test_roundtrip_string(self, fileaccess):
        original = "Hello, World!"
        encoded = fileaccess._encodeString(original)
        decoded = fileaccess._decodeString(encoded)
        assert decoded == original

    def test_roundtrip_dict(self, fileaccess):
        original = {"key": "value", "nested": [1, 2, 3]}
        encoded = fileaccess._encodeString(original)
        decoded = fileaccess._decodeString(encoded)
        assert decoded == original

    def test_empty_string(self, fileaccess):
        assert fileaccess._encodeString("") == ""
        assert fileaccess._decodeString("") == ""

    def test_none_string(self, fileaccess):
        assert fileaccess._encodeString(None) == ""
        assert fileaccess._decodeString(None) == ""

    def test_unicode_content(self, fileaccess):
        original = "日本語テスト"
        encoded = fileaccess._encodeString(original)
        decoded = fileaccess._decodeString(encoded)
        assert decoded == original


# ========================================================================
# 3. dumpJSON / loadJSON
# ========================================================================
class TestDumpLoadJSON:
    def test_dump_dict(self, fileaccess):
        result = fileaccess.dumpJSON({"a": 1})
        assert json.loads(result) == {"a": 1}

    def test_dump_none(self, fileaccess):
        result = fileaccess.dumpJSON(None)
        assert result == '{}'

    def test_dump_string_passthrough(self, fileaccess):
        result = fileaccess.dumpJSON("already json")
        assert result == "already json"

    def test_dump_bytes_decode(self, fileaccess):
        result = fileaccess.dumpJSON(b'{"key": "val"}')
        assert result == '{"key": "val"}'

    def test_load_empty(self, fileaccess):
        assert fileaccess.loadJSON("") == {}

    def test_load_valid(self, fileaccess):
        assert fileaccess.loadJSON('{"a": 1}') == {"a": 1}

    def test_load_invalid_returns_input(self, fileaccess):
        result = fileaccess.loadJSON("not json at all")
        assert result == "not json at all"

    def test_roundtrip(self, fileaccess):
        data = {"nested": {"list": [1, 2, 3]}, "flag": True}
        dumped = fileaccess.dumpJSON(data)
        loaded = fileaccess.loadJSON(dumped)
        assert loaded == data

    def test_sorted_keys(self, fileaccess):
        result = fileaccess.dumpJSON({"z": 1, "a": 2}, sortkey=True)
        assert result.index('"a"') < result.index('"z"')

    def test_load_caching(self, fileaccess):
        data = '{"cached": true}'
        r1 = fileaccess.loadJSON(data)
        r2 = fileaccess.loadJSON(data)
        assert r1 == r2


# ========================================================================
# 4. dumpPICKLE / loadPICKLE
# ========================================================================
class TestDumpLoadPICKLE:
    def test_roundtrip_dict(self, fileaccess):
        data = {"key": "value", "num": 42}
        pickled = fileaccess.dumpPICKLE(data)
        assert isinstance(pickled, bytes)
        unpickled = fileaccess.loadPICKLE(pickled)
        assert unpickled == data

    def test_roundtrip_list(self, fileaccess):
        data = [1, 2, "three", 4.0]
        pickled = fileaccess.dumpPICKLE(data)
        unpickled = fileaccess.loadPICKLE(pickled)
        assert unpickled == data

    def test_none_input(self, fileaccess):
        assert fileaccess.dumpPICKLE(None) == b""
        assert fileaccess.loadPICKLE(None) is None

    def test_empty_input(self, fileaccess):
        assert fileaccess.loadPICKLE("") is None

    def test_bytes_passthrough(self, fileaccess):
        data = b"raw bytes"
        result = fileaccess.dumpPICKLE(data)
        assert result == data

    def test_invalid_pickle(self, fileaccess):
        result = fileaccess.loadPICKLE(b"not valid pickle data")
        assert result is None


# ========================================================================
# 5. _getFolderPath
# ========================================================================
class TestGetFolderPath:
    def test_normal_path(self, fileaccess):
        result = fileaccess._getFolderPath("/some/path/file.txt")
        assert "path" in result
        assert "file.txt" in result

    def test_single_component(self, fileaccess):
        result = fileaccess._getFolderPath("file.txt")
        assert result == "file.txt"


# ========================================================================
# 6. _getShortPath
# ========================================================================
class TestGetShortPath:
    def test_short_path_unchanged(self, fileaccess):
        result = fileaccess._getShortPath("/a/b", max_parts=3)
        assert result == "/a/b"

    def test_long_path_truncated(self, fileaccess):
        path = os.sep.join(["", "a", "b", "c", "d", "e"])
        result = fileaccess._getShortPath(path, max_parts=3)
        assert result.startswith("...")
        parts = result.split(os.sep)
        assert len(parts) >= 4

    def test_short_path_no_truncation(self, fileaccess):
        result = fileaccess._getShortPath("/a/b", max_parts=5)
        assert result == "/a/b"


# ========================================================================
# 7. dump/load JSON roundtrip
# ========================================================================
class TestGetSetJSON:
    def test_dump_load_json_roundtrip(self, fileaccess):
        data = {"test": "data", "number": 123, "nested": [1, 2, 3]}
        dumped = fileaccess.dumpJSON(data, idnt=4)
        loaded = fileaccess.loadJSON(dumped)
        assert loaded == data

    def test_getjson_missing_file(self, fileaccess):
        result = fileaccess.getJSON("/nonexistent/path/file.json")
        assert result is not None
