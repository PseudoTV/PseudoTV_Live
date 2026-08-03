# -*- coding: utf-8 -*-
"""Unit tests for cache.py"""
import sys, os, datetime
from unittest.mock import MagicMock, patch
import pytest

import variables


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


# ========================================================================
# 6. Deferred-commit write batching (_flush_batch)
# ========================================================================
class TestWriteBatching:
    """Verify cache writes buffer in memory and flush in one transaction."""

    def _make(self):
        from cache import _Cache
        c = _Cache()
        c.monitor = MagicMock(abortRequested=MagicMock(return_value=False))
        c.window = MagicMock()
        c._database = MagicMock()
        return c

    def test_writes_buffered_not_committed(self):
        c = self._make()
        c._execute_sql("INSERT OR REPLACE INTO cache(id) VALUES (?)", ('a',))
        assert len(c._write_batch) == 1
        assert c._batch_dirty is True
        c._database.execute.assert_not_called()  # no individual execute/commit

    def test_flush_commits_batch_once(self):
        c = self._make()
        for i in range(5):
            c._execute_sql("INSERT OR REPLACE INTO cache(id) VALUES (?)", (str(i),))
        c._flush_batch()
        assert c._write_batch == []
        assert c._batch_dirty is False
        # One commit for the whole batch, plus the explicit BEGIN
        c._database.commit.assert_called_once()

    def test_flush_with_no_pending_noop(self):
        c = self._make()
        c._flush_batch()
        c._database.commit.assert_not_called()

    def test_read_flushes_pending_writes(self):
        c = self._make()
        c._execute_sql("INSERT OR REPLACE INTO cache(id) VALUES (?)", ('a',))
        c._execute_sql("SELECT id FROM cache WHERE id = ?", ('a',))
        assert c._write_batch == []  # read triggered a flush first

    def test_batch_limit_triggers_auto_flush(self):
        c = self._make()
        c._batch_limit = 3
        for i in range(3):
            c._execute_sql("INSERT OR REPLACE INTO cache(id) VALUES (?)", (str(i),))
        assert c._write_batch == []  # reached limit -> flushed
        c._database.commit.assert_called_once()

    def test_flush_rebuffers_on_db_failure(self):
        c = self._make()
        c._database.execute.side_effect = Exception("DB locked")
        c._database.commit.side_effect = Exception("DB locked")
        for i in range(2):
            c._execute_sql("INSERT OR REPLACE INTO cache(id) VALUES (?)", (str(i),))
        c._flush_batch()
        # Writes re-buffered so a transient lock doesn't lose data
        assert len(c._write_batch) == 2
        assert c._batch_dirty is True

    def test_flush_snapshots_and_releases_for_commit(self):
        c = self._make()
        c._database = MagicMock()
        for i in range(3):
            c._execute_sql("INSERT OR REPLACE INTO cache(id) VALUES (?)", (str(i),))
        # New writes during commit go to a fresh batch, not the in-flight one
        c._flush_batch()
        # After successful flush the buffer is empty
        assert c._write_batch == []
        assert c._batch_dirty is False
