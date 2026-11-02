"""Group 2: frozen provenance, native horizons, runtime connections and atomic capture."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row, tuple_row

from bdf.forecast_snapshots import (
    capture_scenario_snapshots, capture_trajectory_snapshots,
    compute_benchmark_snapshots, compute_horizon, snapshot_id,
)
from bdf.pipeline import ingest
from bdf.worker import drain

DEBT = 'br.debt.gross_pct_gdp'


@pytest.mark.parametrize('frequency,start,end,expected', [
    ('daily', '2024-02-28', '2024-03-01', 2),
    ('monthly', '2024-12-01', '2026-01-01', 13),
    ('quarterly', '2024-12-01', '2025-06-01', 2),
    ('annual', '2024-12-01', '2026-12-01', 2),
    ('monthly', '2025-02-01', '2025-01-01', -1),
])
def test_native_horizon(frequency, start, end, expected):
    assert compute_horizon(frequency, date.fromisoformat(start), date.fromisoformat(end)) == expected


def test_invalid_horizon():
    with pytest.raises(ValueError):
        compute_horizon('quarterly', date(2024, 1, 1), date(2024, 2, 1))
    with pytest.raises(ValueError):
        compute_horizon('weekly', date(2024, 1, 1), date(2024, 2, 1))


def seed(db):
    ingest(db, DEBT, Path('fixtures/debt-initial.json').read_bytes(), 'fixture:snapshot-test')


@pytest.mark.parametrize('factory', [dict_row, tuple_row])
def test_trajectory_capture_native_frequency_and_idempotence(db, factory):
    with psycopg.connect(db, row_factory=factory) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SELECT clock_timestamp() AS now')
            origin = cur.fetchone()['now']
        first = capture_trajectory_snapshots(conn, origin, 'fixture')
        assert first['inserted'] == 36
        assert first['skipped']['interval_dropped_no_nominal_level'] == 36
        assert capture_trajectory_snapshots(conn, origin, 'fixture')['inserted'] == 0
        assert capture_trajectory_snapshots(conn, origin, 'fixture')['inserted'] == 0
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM forecast_snapshot WHERE source_ref='traj-debt-2025'")
            row = cur.fetchone()
            assert (row['frequency'], row['horizon']) == ('monthly', 12)
            assert row['origin_kind'] == 'reconstructed'
            assert row['lower_value'] is None and row['interval_level'] is None
            cur.execute("SELECT DISTINCT frequency FROM forecast_snapshot WHERE indicator_id='br.fx.usd_brl.ptax'")
            assert cur.fetchone()['frequency'] == 'daily'


def test_trajectory_temporal_filters(db):
    with psycopg.connect(db) as conn:
        assert capture_trajectory_snapshots(conn, datetime(2020, 1, 1, tzinfo=timezone.utc))['inserted'] == 0
        with pytest.raises(ValueError, match='timezone'):
            capture_trajectory_snapshots(conn, datetime(2025, 1, 1))
        with pytest.raises(ValueError, match='future'):
            capture_trajectory_snapshots(conn, datetime.now(timezone.utc) + timedelta(days=1))


def test_benchmarks_use_only_origin_vintage_and_same_mode(db):
    seed(db)
    with psycopg.connect(db) as conn:
        origin = conn.execute('SELECT clock_timestamp()').fetchone()[0]
    ingest(db, DEBT, Path('fixtures/debt-revised.json').read_bytes(), 'fixture:later-revision')
    snap = dict(indicator_id=DEBT, target_period=date(2026, 2, 1),
                forecast_origin_at=origin, horizon=12, frequency='monthly',
                unit='percent_gdp', origin_kind='reconstructed', mode='fixture')
    with psycopg.connect(db, row_factory=dict_row) as conn:
        result = compute_benchmark_snapshots(conn, [snap])
        assert result['inserted'] == 2
        rows = conn.execute('SELECT * FROM forecast_snapshot').fetchall()
        assert {r['point_value'] for r in rows} == {Decimal('71')}
        assert all(r['source_ref'] is None for r in rows)
        assert compute_benchmark_snapshots(conn, [snap])['inserted'] == 0
        assert compute_benchmark_snapshots(conn, [dict(snap, mode='source')])['inserted'] == 0
        daily = dict(snap, target_period=date(2026, 3, 1), frequency='daily')
        assert compute_benchmark_snapshots(conn, [daily])['inserted'] == 1


def test_worker_captures_runs_and_replay_is_idempotent(db):
    seed(db)
    assert drain(db)['failed'] == 0
    with psycopg.connect(db, row_factory=dict_row) as conn:
        rows = conn.execute("SELECT s.*, r.created_at AS run_origin FROM forecast_snapshot s JOIN scenario_run r ON r.id=s.source_ref").fetchall()
        assert len(rows) == 12
        assert all(r['origin_kind'] == 'reconstructed' and r['mode'] == 'fixture' for r in rows)
        assert all(r['forecast_origin_at'] == r['run_origin'] and r['input_vintage_id'] for r in rows)
        assert {r['horizon'] for r in rows} == {12, 24, 36, 48}
        run_id = rows[0]['source_ref']
        assert capture_scenario_snapshots(conn, run_id)['inserted'] == 0
        count = conn.execute('SELECT count(*) AS n FROM forecast_snapshot').fetchone()['n']
        conn.execute("UPDATE outbox SET status='pending', processed_at=NULL")
    assert drain(db)['failed'] == 0
    with psycopg.connect(db, row_factory=dict_row) as conn:
        assert conn.execute('SELECT count(*) AS n FROM forecast_snapshot').fetchone()['n'] == count


def test_capture_failure_rolls_back_worker_outputs(db, monkeypatch):
    seed(db)
    def fail(*args):
        raise RuntimeError('snapshot capture failed')
    monkeypatch.setattr('bdf.worker.capture_scenario_snapshots', fail)
    assert drain(db)['failed'] == 6
    with psycopg.connect(db) as conn:
        assert conn.execute('SELECT count(*) FROM scenario_run').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM forecast_snapshot').fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM outbox WHERE status='dead_letter' AND last_error LIKE '%snapshot capture failed%'").fetchone()[0] == 2


def test_snapshot_identity_normalizes_timezones():
    origin = datetime(2025, 1, 1, tzinfo=timezone.utc)
    snap = dict(indicator_id=DEBT, target_period=date(2026, 1, 1), forecast_origin_at=origin,
                forecast_source='scenario_run', model_version='v1', mode='source')
    assert snapshot_id(snap) == snapshot_id(dict(snap, forecast_origin_at=origin.astimezone(timezone(timedelta(hours=-3)))))
    assert snapshot_id(snap) != snapshot_id(dict(snap, mode='fixture'))


def test_source_scenario_is_ex_ante_without_mixing_fixture(db):
    # Synthetic contract input; this is not official economic evidence.
    ingest(db, DEBT, Path('fixtures/debt-initial.json').read_bytes(), 'test:source-contract', mode='source')
    assert drain(db)['failed'] == 0
    with psycopg.connect(db, row_factory=dict_row) as conn:
        rows = conn.execute("SELECT * FROM forecast_snapshot WHERE forecast_source='scenario_run'").fetchall()
        assert len(rows) == 12
        assert all(r['origin_kind'] == 'ex_ante' and r['mode'] == 'source' for r in rows)


def test_trajectory_capture_is_atomic(db, monkeypatch):
    import bdf.forecast_snapshots as module
    original = module._insert_snapshot
    calls = 0
    def fail_second(conn, snap):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('capture interrupted')
        return original(conn, snap)
    monkeypatch.setattr(module, '_insert_snapshot', fail_second)
    with psycopg.connect(db) as conn:
        origin = conn.execute('SELECT clock_timestamp()').fetchone()[0]
        with pytest.raises(RuntimeError, match='capture interrupted'):
            capture_trajectory_snapshots(conn, origin, 'fixture')
        assert conn.execute('SELECT count(*) FROM forecast_snapshot').fetchone()[0] == 0


@pytest.mark.parametrize('latest_period,expected_horizons,skipped_targets', [
    ('01/09/2025', [5, 17, 29, 41], 0),
    ('01/02/2026', [12, 24, 36], 1),
    ('01/03/2026', [11, 23, 35], 1),
])
def test_queued_vintages_measure_horizon_at_run_origin(db, latest_period, expected_horizons, skipped_targets):
    seed(db)
    # Both publications are known before the worker creates the older event's run.
    body = ('[{"data":"' + latest_period + '","valor":"73"}]').encode()
    ingest(db, DEBT, body, 'fixture:newer-period')
    # Even newer data in another mode must not affect fixture horizons.
    ingest(db, DEBT, b'[{"data":"01/10/2026","valor":"74"}]', 'test:other-mode', mode='source')
    assert drain(db)['failed'] == 0
    with psycopg.connect(db, row_factory=dict_row) as conn:
        run = conn.execute("""SELECT * FROM scenario_run WHERE scenario_id='continuity'
                              AND mode='fixture' AND inputs->>'reference_period'='2025-02-01'""").fetchone()
        rows = conn.execute("SELECT * FROM forecast_snapshot WHERE source_ref=%s ORDER BY target_period", (run['id'],)).fetchall()
        assert [r['horizon'] for r in rows] == expected_horizons
        expected_years = range(2026 + skipped_targets, 2030)
        assert [r['target_period'] for r in rows] == [date(y, 2, 1) for y in expected_years]
        assert all(str(r['input_vintage_id']) == run['inputs']['vintage_id'] for r in rows)
        for row in rows:
            benchmark = conn.execute("""SELECT * FROM forecast_snapshot WHERE
                forecast_source='benchmark_random_walk' AND mode='fixture'
                AND forecast_origin_at=%s AND target_period=%s""",
                (run['created_at'], row['target_period'])).fetchone()
            assert benchmark['horizon'] == row['horizon']
            assert benchmark['point_value'] == Decimal('73')
        result = capture_scenario_snapshots(conn, run['id'])
        assert result['inserted'] == 0
        assert result['skipped'].get('target_not_after_latest_known_period', 0) == skipped_targets
        original_ids = [r['id'] for r in rows]
    # A later publication must not alter horizons on replay of the frozen origin.
    ingest(db, DEBT, b'[{"data":"01/04/2026","valor":"75"}]', 'fixture:after-origin')
    with psycopg.connect(db, row_factory=dict_row) as conn:
        assert capture_scenario_snapshots(conn, run['id'])['inserted'] == 0
        rows = conn.execute("SELECT * FROM forecast_snapshot WHERE source_ref=%s ORDER BY target_period", (run['id'],)).fetchall()
        assert [r['id'] for r in rows] == original_ids
        assert [r['horizon'] for r in rows] == expected_horizons
