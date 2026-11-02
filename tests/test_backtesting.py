"""Synthetic contract cases; none of these payloads represent official evidence."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal

import psycopg
import pytest
from psycopg.rows import dict_row, tuple_row

from bdf.backtesting import bias, interval_coverage, mae, match_realized, relative_mae, rmse, run_backtest

ORIGIN = datetime(2024, 1, 15, tzinfo=timezone.utc)
FIRST = datetime(2024, 3, 1, tzinfo=timezone.utc)
REVISION = datetime(2024, 4, 1, tzinfo=timezone.utc)
BEFORE_REVISION = datetime(2024, 3, 15, tzinfo=timezone.utc)
CUTOFF = datetime(2024, 5, 1, tzinfo=timezone.utc)
INDICATOR = 'br.ipca.12m'


def observation(conn, value, period='2024-02-01', known_at=FIRST, mode='source', unit='percent_year'):
    run_id, vintage_id, obs_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    raw_id = uuid.uuid4().hex
    conn.execute('INSERT INTO raw_capture(id,body) VALUES (%s,%s)', (raw_id, b'[]'))
    conn.execute('''INSERT INTO ingestion_run
        (id,indicator_id,captured_at,source_uri,raw_hash,mode,status)
        VALUES (%s,%s,%s,'test:synthetic',%s,%s,'accepted')''', (run_id, INDICATOR, known_at, raw_id, mode))
    conn.execute('''INSERT INTO vintage(id,run_id,known_at,methodology_version,quality_status)
        VALUES (%s,%s,%s,'test-v1','accepted')''', (vintage_id, run_id, known_at))
    conn.execute('''INSERT INTO observation(id,indicator_id,reference_period,value,unit,vintage_id,mode)
        VALUES (%s,%s,%s,%s,%s,%s,%s)''', (obs_id, INDICATOR, period, value, unit, vintage_id, mode))
    return obs_id


def snapshot(conn, value='18', **overrides):
    row = dict(id=uuid.uuid4().hex, indicator_id=INDICATOR, target_period=date(2024, 2, 1),
               forecast_origin_at=ORIGIN, created_at=ORIGIN, horizon=1, frequency='monthly',
               forecast_source='trajectory', source_ref='test:trajectory', model_version='test-v1',
               point_value=value, lower_value=None, upper_value=None, interval_level=None,
               unit='percent_year', origin_kind='ex_ante', mode='source')
    row.update(overrides)
    cols = ','.join(row)
    params = ','.join(f'%({key})s' for key in row)
    conn.execute(f'INSERT INTO forecast_snapshot ({cols}) VALUES ({params})', row)
    return row


def test_metrics_known_errors_and_intervals():
    pairs = [('18', '20'), ('46', '40')]
    assert mae(pairs) == 4
    assert bias(pairs) == 2
    assert rmse(pairs) == Decimal(20).sqrt()
    assert interval_coverage([(17, 22, 20), (44, 48, 40), (None, None, 99)]) == Decimal('0.5')
    assert interval_coverage([(None, None, 20)]) is None
    assert interval_coverage([(20, 20, 20)]) == 1
    assert relative_mae(pairs, [(19, 20), (44, 40)]) == Decimal('1.6')
    assert relative_mae(pairs, [(20, 20), (40, 40)]) is None
    assert relative_mae([], []) is None


@pytest.mark.parametrize('function', [mae, rmse, bias])
def test_metrics_reject_empty_and_nonfinite(function):
    with pytest.raises(ValueError):
        function([])
    with pytest.raises(ValueError):
        function([('NaN', '1')])


def test_invalid_comparisons_rejected():
    with pytest.raises(ValueError):
        interval_coverage([(1, None, 2)])
    with pytest.raises(ValueError):
        relative_mae([(1, 2)], [])
    with pytest.raises(ValueError):
        relative_mae([(1, 2)], [(1, 3)])


@pytest.mark.parametrize('factory', [dict_row, tuple_row])
def test_first_latest_and_temporal_cutoff(db, factory):
    with psycopg.connect(db, row_factory=factory) as conn:
        first_id = observation(conn, '20')
        latest_id = observation(conn, '22', known_at=REVISION)
        snap = snapshot(conn)
        assert match_realized(conn, snap, 'first_release', CUTOFF)['id'] == first_id
        assert match_realized(conn, snap, 'latest', CUTOFF)['id'] == latest_id
        assert match_realized(conn, snap, 'latest', BEFORE_REVISION)['id'] == first_id
        assert match_realized(conn, snap, 'first_release', ORIGIN) is None
        result = run_backtest(conn, CUTOFF, 'source')
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SELECT target,mae FROM backtest_metric WHERE run_id=%s', (result['run_id'],))
            assert {r['target']: r['mae'] for r in cur.fetchall()} == {'first_release': 2, 'latest': 4}


@pytest.mark.parametrize('origin', [FIRST, REVISION])
def test_already_known_realized_is_not_rehabilitated_by_revision(db, origin):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        observation(conn, '20')
        observation(conn, '22', known_at=REVISION)
        snap = snapshot(conn, forecast_origin_at=origin, created_at=origin)
        for target in ('first_release', 'latest'):
            assert match_realized(conn, snap, target, CUTOFF) is None
        assert run_backtest(conn, CUTOFF, 'source')['metrics'] == 0


def test_run_metrics_groups_benchmarks_and_idempotency(db):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        observation(conn, '20')
        observation(conn, '40', period='2024-03-01')
        snapshot(conn, lower_value=17, upper_value=22, interval_level='.8')
        snapshot(conn, value='46', target_period=date(2024, 3, 1), lower_value=44, upper_value=48, interval_level='.8')
        for period, value in [(date(2024, 2, 1), 19), (date(2024, 3, 1), 44)]:
            snapshot(conn, value=value, target_period=period, forecast_source='benchmark_random_walk', source_ref=None)
        snapshot(conn, value='30', origin_kind='reconstructed', model_version='reconstruction-v1')
        # A fixture with the same indicator/period cannot become the source realized.
        observation(conn, '999', mode='fixture')
        result = run_backtest(conn, CUTOFF, 'source')
        row = conn.execute('''SELECT * FROM backtest_metric WHERE run_id=%s AND
            forecast_source='trajectory' AND target='first_release' AND origin_kind='ex_ante' ''', (result['run_id'],)).fetchone()
        assert row['n_obs'] == 2 and row['insufficient_sample'] is True
        assert row['mae'] == 4 and row['bias'] == 2
        assert row['rmse'] == Decimal(20).sqrt()
        assert row['interval_coverage'] == Decimal('.5')
        assert row['relative_mae_vs_rw'] == Decimal('1.6')
        separate = conn.execute('''SELECT * FROM backtest_metric WHERE run_id=%s AND
            origin_kind='reconstructed' AND target='first_release' ''', (result['run_id'],)).fetchone()
        assert separate['n_obs'] == 1 and separate['mae'] == 10
        assert separate['relative_mae_vs_rw'] is None  # cannot borrow an ex-ante benchmark
        repeated = run_backtest(conn, CUTOFF, 'source')
        assert repeated['run_id'] == result['run_id'] and repeated['reused'] is True
        assert run_backtest(conn, CUTOFF, 'fixture')['metrics'] == 0


def test_relative_mae_requires_complete_benchmark_sample(db):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        observation(conn, '20')
        observation(conn, '40', period='2024-03-01')
        snapshot(conn, value='18')
        snapshot(conn, value='100', target_period=date(2024, 3, 1))
        snapshot(conn, value='19', forecast_source='benchmark_random_walk', source_ref=None)
        result = run_backtest(conn, CUTOFF, 'source')
        row = conn.execute('''SELECT * FROM backtest_metric WHERE run_id=%s AND
            forecast_source='trajectory' AND target='first_release' ''', (result['run_id'],)).fetchone()
        assert row['mae'] == 31 and row['n_obs'] == 2
        assert row['relative_mae_vs_rw'] is None  # no ratio on a smaller, unlabelled sample
        assert row['interval_coverage'] is None


def test_snapshots_created_after_cutoff_excluded_and_empty_run_reused(db):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        observation(conn, '20')
        snapshot(conn, created_at=datetime(2024, 6, 1, tzinfo=timezone.utc))
        result = run_backtest(conn, CUTOFF, 'source')
        assert result['metrics'] == 0
        assert run_backtest(conn, CUTOFF, 'source')['run_id'] == result['run_id']


def test_changed_revision_changes_inputs_hash(db):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        observation(conn, '20')
        snapshot(conn)
        first = run_backtest(conn, CUTOFF, 'source')
        observation(conn, '22', known_at=REVISION)
        revised = run_backtest(conn, CUTOFF, 'source')
        assert first['run_id'] != revised['run_id']
        assert conn.execute('SELECT count(*) AS n FROM backtest_run').fetchone()['n'] == 2


def test_incompatible_unit_rolls_back_run(db):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        observation(conn, '20', unit='percent_month')
        snapshot(conn)
        with pytest.raises(ValueError, match='unit'):
            run_backtest(conn, CUTOFF, 'source')
        assert conn.execute('SELECT count(*) AS n FROM backtest_run').fetchone()['n'] == 0
        assert conn.execute('SELECT count(*) AS n FROM backtest_metric').fetchone()['n'] == 0


def test_sample_threshold_and_zero_benchmark_error(db):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        for year in range(2010, 2018):
            period = date(year, 2, 1)
            observation(conn, '20', period=period)
            snapshot(conn, target_period=period, origin_kind='reconstructed')
            snapshot(conn, value='20', target_period=period, origin_kind='reconstructed',
                     forecast_source='benchmark_random_walk', source_ref=None)
        result = run_backtest(conn, CUTOFF, 'source')
        row = conn.execute('''SELECT * FROM backtest_metric WHERE run_id=%s AND
            forecast_source='trajectory' AND target='first_release' ''', (result['run_id'],)).fetchone()
        assert row['n_obs'] == 8 and row['insufficient_sample'] is False
        assert row['relative_mae_vs_rw'] is None


def test_concurrent_run_is_idempotent(db):
    with psycopg.connect(db) as conn:
        observation(conn, '20')
        snapshot(conn)
    def execute():
        with psycopg.connect(db, row_factory=dict_row) as conn:
            return run_backtest(conn, CUTOFF, 'source')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: execute(), range(2)))
    assert results[0]['run_id'] == results[1]['run_id']
    assert sum(not r['reused'] for r in results) == 1


def test_invalid_run_parameters(db):
    with psycopg.connect(db) as conn:
        with pytest.raises(ValueError, match='timezone'):
            run_backtest(conn, datetime(2024, 1, 1), 'fixture')
        with pytest.raises(ValueError, match='mode'):
            run_backtest(conn, CUTOFF, 'official')
        with pytest.raises(ValueError, match='future'):
            run_backtest(conn, datetime(2999, 1, 1, tzinfo=timezone.utc), 'fixture')


def test_metric_failure_rolls_back_entire_run(db, monkeypatch):
    import bdf.backtesting as module
    original = module.bias
    calls = 0
    def fail_second(pairs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ArithmeticError('metric failed after first insert')
        return original(pairs)
    with psycopg.connect(db, row_factory=dict_row) as conn:
        observation(conn, '20')
        snapshot(conn)
        monkeypatch.setattr(module, 'bias', fail_second)
        with pytest.raises(ArithmeticError):
            run_backtest(conn, CUTOFF, 'source')
        assert calls == 2
        assert conn.execute('SELECT count(*) AS n FROM backtest_run').fetchone()['n'] == 0
        assert conn.execute('SELECT count(*) AS n FROM backtest_metric').fetchone()['n'] == 0


def test_minimum_sample_is_part_of_reproducible_inputs(db, monkeypatch):
    import bdf.backtesting as module
    with psycopg.connect(db, row_factory=dict_row) as conn:
        observation(conn, '20')
        snapshot(conn)
        initial = run_backtest(conn, CUTOFF, 'source')
        monkeypatch.setattr(module, 'MIN_SAMPLE', 1)
        changed = run_backtest(conn, CUTOFF, 'source')
        assert changed['run_id'] != initial['run_id']
        assert conn.execute('SELECT min_sample FROM backtest_run WHERE id=%s', (changed['run_id'],)).fetchone()['min_sample'] == 1
        assert conn.execute('SELECT insufficient_sample FROM backtest_metric WHERE run_id=%s LIMIT 1', (changed['run_id'],)).fetchone()['insufficient_sample'] is False


def test_cli_uses_explicit_cutoff_and_mode(db, monkeypatch, capsys):
    import json
    from bdf.backtesting import main
    monkeypatch.setenv('DATABASE_URL', db)
    main(['--as-of', CUTOFF.isoformat(), '--mode', 'fixture'])
    first = json.loads(capsys.readouterr().out)
    main(['--as-of', CUTOFF.isoformat(), '--mode', 'fixture'])
    second = json.loads(capsys.readouterr().out)
    assert first['experimental'] is True and first['mode'] == 'fixture'
    assert second['reused'] is True and second['run_id'] == first['run_id']
    with pytest.raises(SystemExit) as exc:
        main(['--as-of', '2024-05-01', '--mode', 'fixture'])
    assert exc.value.code == 2
