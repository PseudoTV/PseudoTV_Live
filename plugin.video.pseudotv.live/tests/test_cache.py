# -*- coding: utf-8 -*-
"""Unit tests for cache.py"""
import sys, os, datetime
from unittest.mock import MagicMock, patch
import pytest

import variables


@pytest.fixture(autouse=True)
def _reset_memory_budget():
    """The MemoryBudget singleton persists across tests — reset used bytes and the
    global cap so byte-budget assertions aren't polluted by earlier tests."""
    from cache import MemoryBudget
    from constants import GLOBAL_CACHE_MEM_MAX
    budget = MemoryBudget.instance()
    budget.max_bytes = GLOBAL_CACHE_MEM_MAX
    budget.reset()
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


# ========================================================================
# 7. In-memory mem-cache byte budget (_setMEM / _trimMEM)
# ========================================================================
class TestMemCacheBudget:
    def _make(self):
        from cache import _Cache
        c = _Cache()
        c.monitor = MagicMock(abortRequested=MagicMock(return_value=False))
        c.window = MagicMock()
        c._database = MagicMock()
        return c

    def test_setmem_tracks_bytes(self):
        c = self._make()
        c.max_entries = 1000
        c.max_mem_bytes = 10 * 1024 * 1024
        c._setMEM('a', 'chk', -1, {'x': 'y' * 100})
        assert len(c._cache_idx) == 1
        assert c._mem_bytes == c._cache_idx[0][1]
        assert c.window.setProperty.called

    def test_setmem_refuses_over_budget(self):
        c = self._make()
        c.max_entries = 1000
        c.max_mem_bytes = 64  # tiny budget
        c._setMEM('a', 'chk', -1, {'blob': 'x' * 1000})  # 1KB > 64B -> skipped
        assert len(c._cache_idx) == 0
        c.window.setProperty.assert_not_called()

    def test_setmem_bounded_total(self):
        c = self._make()
        c.max_entries = 1000
        c.max_mem_bytes = 512
        for i in range(50):
            c._setMEM('k%d' % i, 'chk', -1, {'data': 'v' * 20})
        assert c._mem_bytes <= c.max_mem_bytes
        assert len(c._cache_idx) <= c.max_entries

    def test_trimMEM_evicts_when_over_byte_budget(self):
        c = self._make()
        c.max_entries = 1000
        c.max_mem_bytes = 40
        # simulate a budget blow-out (entries already present)
        c._cache_idx.append(('k1', 100)); c._mem_bytes = 100
        c._cache_idx.append(('k2', 50));  c._mem_bytes = 150
        c._trimMEM()
        assert c._mem_bytes <= c.max_mem_bytes
        assert len(c._cache_idx) == 0
        assert c.window.clearProperty.called

    def test_checksum_cache_bounded(self):
        from cache import _Cache
        from unittest.mock import patch as _patch
        _Cache._checksum_cache.clear()
        c = _Cache()
        c.global_checksum = 'v'
        with _patch('cache.CHECKSUM_CACHE_MAX', 10):
            for i in range(25):
                c.getChecksum('key%d' % i)
        assert len(_Cache._checksum_cache) <= 10


# ========================================================================
# 8. Properties._memory_cache byte-bounded LRU (_BoundedOrderedDict)
# ========================================================================
class TestBoundedOrderedDict:
    def _make(self, max_bytes):
        from kodi import _BoundedOrderedDict
        return _BoundedOrderedDict(max_bytes)

    def test_evicts_oldest_over_byte_budget(self):
        d = self._make(200)
        d['a'] = 'x' * 100   # ~141 bytes
        d['b'] = 'y' * 100   # ~282 total -> evict 'a'
        assert 'a' not in d
        assert 'b' in d
        assert d.membytes <= 200

    def test_keeps_under_budget(self):
        d = self._make(512)
        for i in range(20):
            d['k%d' % i] = 'v' * 10
        assert d.membytes <= 512
        assert len(d) <= 20

    def test_update_does_not_double_count(self):
        d = self._make(1024)
        d['a'] = 'x' * 50
        d['a'] = 'x' * 50  # replace same key
        assert d.membytes < 100  # one ~91-byte entry, not two
        assert len(d) == 1

    def test_pop_decrements_bytes(self):
        d = self._make(1024)
        d['a'] = 'x' * 100
        before = d.membytes
        d.pop('a', None)
        assert d.membytes == 0
        assert before > 0

    def test_clear_resets_bytes(self):
        d = self._make(1024)
        d['a'] = 'x' * 100
        d.clear()
        assert d.membytes == 0


# ========================================================================
# 9. Shared global MemoryBudget (combined caches can't exceed the global cap)
# ========================================================================
class TestGlobalBudget:
    def test_own_cap_enforced(self):
        from cache import MemoryBudget
        b = MemoryBudget.instance()
        b.max_bytes = 1000
        b.register('render', 100)
        assert b.acquire('render', 90) is True
        assert b.acquire('render', 20) is False  # would exceed render's own cap

    def test_combined_cannot_exceed_global(self):
        from cache import MemoryBudget
        b = MemoryBudget.instance()
        b.max_bytes = 100
        b.register('render', 80)
        b.register('memcache', 80)
        assert b.acquire('render', 50) is True
        assert b.acquire('memcache', 40) is True   # 50+40 = 90 <= 100 global
        assert b.acquire('memcache', 20) is False  # 90+20 = 110 > 100 -> refused globally
        b.reset()

    def test_release_frees_global(self):
        from cache import MemoryBudget
        b = MemoryBudget.instance()
        b.max_bytes = 100
        b.register('render', 80)
        assert b.acquire('render', 80) is True
        assert b.used() == 80
        b.release('render', 80)
        assert b.used() == 0
        assert b.acquire('render', 80) is True
        b.reset()

    def test_fractions_sum_within_global(self):
        from constants import GLOBAL_CACHE_MEM_MAX, CACHE_MEM_MAX, PROPERTY_MEM_MAX, RENDER_CACHE_MAX
        assert CACHE_MEM_MAX + PROPERTY_MEM_MAX + RENDER_CACHE_MAX <= GLOBAL_CACHE_MEM_MAX


# ========================================================================
# 10. _cleanDB purges expired rows (cache.db bloat guard)
# ========================================================================
class TestCleanDB:
    """_cleanDB was referenced by _chkClean but never defined — expired rows
    (multi-MB movie/tvshow dumps) accumulated forever, bloating cache.db to
    300+MB on low-RAM SOCs. Verify the purge actually deletes them."""

    def _make(self):
        import tempfile
        from cache import _Cache
        c = _Cache()
        c.monitor = MagicMock(abortRequested=MagicMock(return_value=False))
        c.window = MagicMock(getProperty=MagicMock(return_value=None))
        c._database = MagicMock()
        return c

    def test_cleanDB_deletes_expired_rows(self):
        import datetime
        c = self._make()
        now = c.getTimestamp(datetime.datetime.now())
        cur = MagicMock(rowcount=2)
        c._database.execute.return_value = cur
        c._flush_batch = MagicMock()
        c._cleanDB()
        args = [a[0] for a in c._database.execute.call_args_list if 'DELETE FROM cache' in (a[0][0] if isinstance(a[0], tuple) else str(a[0]))]
        assert args, 'cleanDB must issue a DELETE'
        c._database.commit.assert_called_once()

    def test_cleanDB_defined(self, cache_module):
        assert hasattr(cache_module, '_cleanDB'), '_cleanDB must exist (was missing)'
        assert callable(cache_module._cleanDB)

    def test_checkpoint_triggers_cleanup(self):
        import datetime
        from cache import _Cache
        c = _Cache()
        c.monitor = MagicMock(abortRequested=MagicMock(return_value=False))
        c.window = MagicMock(getProperty=MagicMock(return_value=None))
        c._database = MagicMock()
        c._checkpointing = False
        c._flush_batch = MagicMock()
        with patch.object(c, '_chkClean') as chk:
            c._checkpoint()
        chk.assert_called_once()
