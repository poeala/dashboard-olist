"""Cache behavior: persistence, isolation, expiration and multiworker reuse."""
from decimal import Decimal
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data import query_cache
from data.materialized import materialized_state


def concurrent_reader(directory, index):
    os.environ['DASHBOARD_CACHE_DIR'] = directory
    os.environ['DASHBOARD_CACHE_TTL_SECONDS'] = '3600'
    deadline = time.monotonic() + 15
    while not (Path(directory) / 'ready').exists():
        if time.monotonic() > deadline:
            raise TimeoutError('Test start signal missing')
        time.sleep(.02)
    def load():
        with (Path(directory) / 'downloads.txt').open('a') as f:
            f.write('download\n')
        time.sleep(.2)
        return pd.DataFrame({'value': [42]})
    result = query_cache.cached_frame('multiworker', {}, load)
    (Path(directory) / f'result-{index}').write_text(str(int(result.iloc[0]['value'])))


class QueryCacheTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(__file__).resolve().parents[1] / '.cache/cache-tests'
        self.directory = self.base / uuid4().hex
        self.directory.mkdir(parents=True)
        self.env = patch.dict(os.environ, {
            'DASHBOARD_CACHE_DIR': str(self.directory),
            'DASHBOARD_CACHE_TTL_SECONDS': '3600',
            'DASHBOARD_CACHE_VERSION': 'test',
            'DASHBOARD_USE_MATERIALIZED': 'auto',
        })
        self.env.start()
        query_cache._memory.clear()

    def tearDown(self):
        self.env.stop()
        query_cache._memory.clear()
        if not self.directory.resolve().is_relative_to(self.base.resolve()):
            raise AssertionError('Unsafe cleanup directory')
        shutil.rmtree(self.directory)

    def test_preserves_types_attrs_and_independent_copies_across_restart(self):
        frame = pd.DataFrame({'money': [Decimal('2.10')], 'date': [pd.Timestamp('2018-01-01')], 'missing': [None]})
        frame.attrs['cutoff'] = pd.Timestamp('2018-08-31')
        load = Mock(return_value=frame)
        first = query_cache.cached_frame('source', {}, load)
        first.loc[0, 'money'] = Decimal('999')
        second = query_cache.cached_frame('source', {}, load)
        pd.testing.assert_frame_equal(second, frame)
        query_cache._memory.clear()
        third = query_cache.cached_frame('source', {}, load)
        pd.testing.assert_frame_equal(third, frame)
        self.assertEqual(third.attrs, frame.attrs)
        self.assertEqual(load.call_count, 1)

    def test_expiration_and_version_force_a_new_download(self):
        load = Mock(side_effect=[pd.DataFrame({'v': [1]}), pd.DataFrame({'v': [2]}), pd.DataFrame({'v': [3]})])
        query_cache.cached_frame('source', {}, load)
        future = time.time() + 4000
        with patch('data.query_cache.time.time', return_value=future):
            self.assertEqual(query_cache.cached_frame('source', {}, load).iloc[0]['v'], 2)
        with patch.dict(os.environ, {'DASHBOARD_CACHE_VERSION': 'next'}):
            self.assertEqual(query_cache.cached_frame('source', {}, load).iloc[0]['v'], 3)

    def test_query_parameters_do_not_share_results(self):
        load = Mock(return_value=pd.DataFrame({'v': [1]}))
        query_cache.cached_frame('query', {'year': 2017}, load)
        query_cache.cached_frame('query', {'year': 2018}, load)
        query_cache.cached_frame('query', {'year': 2017}, load)
        self.assertEqual(load.call_count, 2)

    def test_role_and_database_are_part_of_cache_identity(self):
        load = Mock(return_value=pd.DataFrame({'v': [1]}))
        query_cache.cached_frame('query', {}, load)
        with patch.object(query_cache, 'DATABASE_URL', query_cache.DATABASE_URL.set(username='another-role')):
            query_cache.cached_frame('query', {}, load)
        self.assertEqual(load.call_count, 2)

    def test_loader_failure_is_not_cached(self):
        load = Mock(side_effect=[RuntimeError('test failure'), pd.DataFrame({'v': [2]})])
        with self.assertRaises(RuntimeError):
            query_cache.cached_frame('source', {}, load)
        self.assertEqual(query_cache.cached_frame('source', {}, load).iloc[0]['v'], 2)

    def test_damaged_cache_is_replaced(self):
        load = Mock(return_value=pd.DataFrame({'v': [1]}))
        query_cache.cached_frame('source', {}, load)
        query_cache._memory.clear()
        with closing(sqlite3.connect(self.directory / 'queries.sqlite3')) as conn:
            conn.execute("UPDATE results SET payload=x'00'")
            conn.commit()
        query_cache.cached_frame('source', {}, load)
        self.assertEqual(load.call_count, 2)

    def test_disabled_cache_reads_each_time(self):
        load = Mock(return_value=pd.DataFrame({'v': [1]}))
        with patch.dict(os.environ, {'DASHBOARD_CACHE_TTL_SECONDS': '0'}):
            query_cache.cached_frame('source', {}, load)
            query_cache.cached_frame('source', {}, load)
        self.assertEqual(load.call_count, 2)

    def test_two_workers_download_only_once(self):
        workers = [subprocess.Popen([sys.executable, __file__, '--cache-worker', str(self.directory), str(i)]) for i in range(2)]
        (self.directory / 'ready').touch()
        try:
            for worker in workers:
                self.assertEqual(worker.wait(timeout=30), 0)
            self.assertEqual([(self.directory / f'result-{i}').read_text() for i in range(2)], ['42', '42'])
            self.assertEqual((self.directory / 'downloads.txt').read_text().splitlines(), ['download'])
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.terminate()
                    worker.wait()


class MaterializedSelectionTests(unittest.TestCase):
    def test_auto_falls_back_only_when_schema_is_absent(self):
        conn = Mock()
        conn.execute.return_value.scalar.return_value = False
        with patch.dict(os.environ, {'DASHBOARD_USE_MATERIALIZED': 'auto'}):
            self.assertIsNone(materialized_state(conn))
        conn.execute.side_effect = PermissionError('access denied')
        with self.assertRaises(PermissionError):
            materialized_state(conn)

    def test_required_materializations_fail_if_not_installed(self):
        conn = Mock()
        conn.execute.return_value.scalar.return_value = False
        with patch.dict(os.environ, {'DASHBOARD_USE_MATERIALIZED': 'on'}):
            with self.assertRaises(RuntimeError):
                materialized_state(conn)

    def test_disabled_mode_never_checks_database(self):
        conn = Mock()
        with patch.dict(os.environ, {'DASHBOARD_USE_MATERIALIZED': 'off'}):
            self.assertIsNone(materialized_state(conn))
        conn.execute.assert_not_called()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--cache-worker':
        concurrent_reader(sys.argv[2], sys.argv[3])
    else:
        unittest.main()
