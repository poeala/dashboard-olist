"""Audit, install, refresh and validate the private BI layer with bounded output.

Never logs connection URLs, passwords, or row-level customer data.
"""
import argparse
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import DATABASE_URL
from data.definitions import PERIOD_CUTOFF_SQL
from data.materialized import LOGISTICS_SQL, CUSTOMERS_SQL, PAYMENTS_SQL


def queries():
    # Capture the actual legacy SQL without loading a single source row.
    from data import business
    result = []
    with patch.object(business, '_read_snapshot', side_effect=lambda *args: args):
        for name, fn in [('logistics', business.cargar_logistica),
                         ('customers', business.cargar_clientes),
                         ('payments', business.cargar_pagos_bi)]:
            args = fn()
            result.append((name, args[0].rsplit('ORDER BY', 1)[0], args[3].rsplit('ORDER BY', 1)[0]))
    return result


def audit(conn):
    result = {'database_bytes': conn.execute(text('SELECT pg_database_size(current_database())')).scalar()}
    result['gold_indexes'] = [dict(r) for r in conn.execute(text("""
        SELECT t.relname AS table_name, i.relname AS index_name, ix.indisvalid AS valid,
               pg_get_indexdef(i.oid) AS definition
        FROM pg_index ix JOIN pg_class t ON t.oid=ix.indrelid JOIN pg_class i ON i.oid=ix.indexrelid
        JOIN pg_namespace n ON n.oid=t.relnamespace
        WHERE n.nspname='public' AND t.relname LIKE 'gld_%' ORDER BY t.relname,i.relname
    """)).mappings()]
    result['materialized_bytes'] = conn.execute(text("""
        SELECT COALESCE(SUM(pg_total_relation_size(c.oid)),0) FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='dashboard_bi' AND c.relkind IN ('m','r')
    """)).scalar()
    return result


def validate(conn, cutoff, explain=False):
    results = {}
    for name, old, new in queries():
        # EXCEPT ALL proves row multiplicity, nulls and values, not just totals.
        differences = conn.execute(text(f"""
            WITH original AS ({old}), optimized AS ({new}),
            missing AS (SELECT * FROM original EXCEPT ALL SELECT * FROM optimized),
            extra AS (SELECT * FROM optimized EXCEPT ALL SELECT * FROM original)
            SELECT (SELECT COUNT(*) FROM missing) + (SELECT COUNT(*) FROM extra)
        """), {'cutoff': cutoff}).scalar()
        if differences:
            raise RuntimeError(f'{name}: {differences} differing rows; transaction rolled back')
        entry = {'different_rows': 0}
        if explain:
            for label, query in [('original', old), ('optimized', new)]:
                plan = conn.execute(text('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + query), {'cutoff': cutoff}).scalar()[0]
                entry[label] = {'execution_ms': plan['Execution Time'], 'rows': plan['Plan']['Actual Rows'],
                                'shared_hit_blocks': plan['Plan'].get('Shared Hit Blocks', 0)}
        results[name] = entry
    return results


def refresh(conn):
    conn.execute(text('REFRESH MATERIALIZED VIEW dashboard_bi.mv_order_context'))
    conn.execute(text('REFRESH MATERIALIZED VIEW dashboard_bi.mv_customer_orders'))
    cutoff = conn.execute(text(PERIOD_CUTOFF_SQL)).scalar()
    conn.execute(text("""
        INSERT INTO dashboard_bi.refresh_state (singleton,schema_version,cutoff,refreshed_at)
        VALUES (true,1,:cutoff,clock_timestamp()) ON CONFLICT (singleton)
        DO UPDATE SET schema_version=EXCLUDED.schema_version, cutoff=EXCLUDED.cutoff,
                      refreshed_at=EXCLUDED.refreshed_at
    """), {'cutoff': cutoff})
    for view in ['mv_order_context', 'mv_customer_orders']:
        conn.execute(text(f'ANALYZE dashboard_bi.{view}'))
    return cutoff


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['audit', 'install', 'refresh', 'verify'])
    parser.add_argument('--dry-run', action='store_true', help='Build and validate, then roll back (no persistent objects)')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 10})
    report = {'action': args.action, 'dry_run': args.dry_run}
    try:
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
                conn.execute(text("SET LOCAL statement_timeout = '180s'"))
                conn.execute(text("SET LOCAL lock_timeout = '5s'"))
                report['before'] = audit(conn)
                if args.action in ('install', 'refresh'):
                    conn.execute(text("SELECT pg_advisory_xact_lock(714120, 1)"))
                    if args.action == 'install':
                        if report['before']['database_bytes'] > 440 * 1024 * 1024:
                            raise RuntimeError('Insufficient free-plan headroom for materializations; use cache only')
                        # SQL file is trusted versioned source, with no user substitutions.
                        conn.exec_driver_sql((ROOT / 'sql/001_dashboard_materialized.sql').read_text(encoding='utf-8'), execution_options={'no_parameters': True})
                    version = conn.execute(text('SELECT schema_version FROM dashboard_bi.refresh_state WHERE singleton')).scalar()
                    if version not in (None, 1):
                        raise RuntimeError('Incompatible materialized schema version')
                    started = time.perf_counter()
                    cutoff = refresh(conn)
                    report['refresh_seconds'] = round(time.perf_counter() - started, 3)
                    report['verification'] = validate(conn, cutoff, explain=True)
                    report['cutoff_exclusive'] = cutoff
                    report['after_materialization'] = audit(conn)
                    if report['after_materialization']['database_bytes'] > 480 * 1024 * 1024:
                        raise RuntimeError('Materializations exceed the configured free-plan safety budget')
                    if args.dry_run:
                        conn.rollback()
                elif args.action == 'verify':
                    cutoff = conn.execute(text('SELECT cutoff FROM dashboard_bi.refresh_state WHERE singleton')).scalar()
                    report['verification'] = validate(conn, cutoff, explain=True)
        if args.action == 'install' and not args.dry_run:
            with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
                conn.exec_driver_sql("SET statement_timeout='180s'")
                conn.exec_driver_sql("SET lock_timeout='5s'")
                conn.exec_driver_sql((ROOT / 'sql/002_dashboard_indexes.sql').read_text(encoding='utf-8'))
                conn.exec_driver_sql('ANALYZE public.gld_sales_detail')
                report['after'] = audit(conn)
        print(json.dumps(report, indent=2, default=str))
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    except Exception as exc:
        # SQLAlchemy errors may contain the connection URL or bound data.
        # Emit a safe type and SQLSTATE, plus controlled validation messages.
        print('FAILED:', type(exc).__name__, getattr(getattr(exc, 'orig', None), 'sqlstate', ''))
        diagnostic = getattr(getattr(exc, 'orig', None), 'diag', None)
        if diagnostic and diagnostic.message_primary:
            print(diagnostic.message_primary)
        if isinstance(exc, RuntimeError):
            print(str(exc))
        raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
