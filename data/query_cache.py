"""Private, shared, persistent cache for historical dashboard queries.

The SQLite file contains only results produced by this backend. It must never
be writable by uploads or served as a public asset (payloads use pickle to
preserve pandas types, dates, Decimal values and DataFrame attrs).
"""
from collections import OrderedDict
from contextlib import closing
import hashlib
import json
import logging
import os
from pathlib import Path
import pickle
import sqlite3
import threading
import time
import zlib

from config import DATABASE_URL

logger = logging.getLogger(__name__)
_memory = OrderedDict()
_lock = threading.RLock()
FORMAT_VERSION = 'olist-cache-v1'


def _settings():
    directory = Path(os.getenv('DASHBOARD_CACHE_DIR', Path(__file__).resolve().parents[1] / '.cache'))
    return directory, max(0, int(os.getenv('DASHBOARD_CACHE_TTL_SECONDS', '86400')))


def _key(name, params):
    identity = DATABASE_URL.render_as_string(hide_password=True)
    body = [FORMAT_VERSION, identity, os.getenv('DASHBOARD_CACHE_VERSION', '1'),
            os.getenv('DASHBOARD_USE_MATERIALIZED', 'auto'), name, params]
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def _remember(key, value, created, ttl):
    _memory[key] = (created, value.copy(deep=True))
    _memory.move_to_end(key)
    # Keep large source frames in RAM; filtered detail/aggregation results stay
    # in SQLite and need not multiply the memory footprint indefinitely.
    while len(_memory) > 12:
        _memory.popitem(last=False)


def cached_frame(name, params, loader):
    """Read once per key/TTL across workers, returning an independent frame.

    BEGIN IMMEDIATE serializes cache misses, including across processes, so
    two Gunicorn workers do not download the same snapshot simultaneously.
    Cache I/O failure fails explicitly instead of silently hammering Supabase.
    """
    directory, ttl = _settings()
    if not ttl:
        return loader()
    key = _key(name, params)
    memory_key = (str(directory.resolve()), key)
    with _lock:
        now = time.time()
        hit = _memory.get(memory_key)
        if hit and 0 <= now - hit[0] < ttl:
            _memory.move_to_end(memory_key)
            return hit[1].copy(deep=True)
        directory.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(directory / 'queries.sqlite3', timeout=180)) as conn:
            conn.execute('PRAGMA busy_timeout=180000')
            conn.execute('CREATE TABLE IF NOT EXISTS results (cache_key TEXT PRIMARY KEY, created REAL NOT NULL, payload BLOB NOT NULL)')
            conn.commit()
            try:
                conn.execute('BEGIN IMMEDIATE')
                now = time.time()
                row = conn.execute('SELECT created, payload FROM results WHERE cache_key=?', (key,)).fetchone()
                if row and 0 <= now - row[0] < ttl:
                    try:
                        result = pickle.loads(zlib.decompress(row[1]))
                    except (pickle.UnpicklingError, zlib.error, EOFError, ValueError):
                        logger.warning('Replacing a damaged private dashboard cache entry')
                    else:
                        conn.commit()
                        _remember(memory_key, result, row[0], ttl)
                        logger.info('dashboard cache hit: %s', name)
                        return result.copy(deep=True)
                result = loader()
                created = time.time()
                payload = zlib.compress(pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL), level=3)
                conn.execute('DELETE FROM results WHERE created < ?', (created - ttl,))
                conn.execute('INSERT OR REPLACE INTO results VALUES (?, ?, ?)', (key, created, payload))
                # Bound stored payloads to 128 MiB. SQLite reuses freed pages;
                # no VACUUM on a request and no deletion of active snapshots.
                total = conn.execute('SELECT COALESCE(SUM(length(payload)),0) FROM results').fetchone()[0]
                for old_key, size in conn.execute('SELECT cache_key,length(payload) FROM results WHERE cache_key<>? ORDER BY created', (key,)).fetchall():
                    if total <= 128 * 1024 * 1024:
                        break
                    conn.execute('DELETE FROM results WHERE cache_key=?', (old_key,))
                    total -= size
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        _remember(memory_key, result, created, ttl)
        logger.info('dashboard cache miss: %s (%s rows)', name, len(result))
        return result.copy(deep=True)


def read_sql_cached(query, engine, params=None):
    import pandas as pd
    return cached_frame('sql:' + str(query), params or {},
                        lambda: pd.read_sql(query, engine, params=params))
