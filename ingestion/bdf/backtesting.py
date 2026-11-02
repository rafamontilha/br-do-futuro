"""Experimental, append-only forecast evaluation against captured vintages.

Errors are forecast minus realized. Reconstructed and ex-ante snapshots are always
separate. Nothing here publishes a recommendation or changes a forecast.
"""
from __future__ import annotations

import argparse
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

from .scenario import fingerprint

CODE_VERSION = 'backtesting-v1'
MIN_SAMPLE = 8
TARGETS = ('first_release', 'latest')


def _number(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Metric inputs must be finite')
    return result


def _errors(pairs):
    errors = [_number(forecast) - _number(actual) for forecast, actual in pairs]
    if not errors:
        raise ValueError('Cannot evaluate an empty sample')
    return errors


def mae(pairs):
    errors = _errors(pairs)
    return sum(map(abs, errors)) / len(errors)


def rmse(pairs):
    errors = _errors(pairs)
    return (sum(error * error for error in errors) / len(errors)).sqrt()


def bias(pairs):
    errors = _errors(pairs)
    return sum(errors) / len(errors)


def interval_coverage(intervals):
    """Fraction covered among complete intervals; absent intervals are excluded.

    Each item is (lower, upper, realized). No declared intervals returns None.
    """
    covered = []
    for lower, upper, actual in intervals:
        if lower is None and upper is None:
            continue
        if lower is None or upper is None:
            raise ValueError('Incomplete forecast interval')
        lower, upper, actual = map(_number, (lower, upper, actual))
        if lower > upper:
            raise ValueError('Reversed forecast interval')
        covered.append(lower <= actual <= upper)
    return Decimal(sum(covered)) / len(covered) if covered else None


def relative_mae(model_pairs, benchmark_pairs):
    """MAE ratio on exactly the same realized sample; zero denominator is undefined."""
    model_pairs, benchmark_pairs = list(model_pairs), list(benchmark_pairs)
    if len(model_pairs) != len(benchmark_pairs):
        raise ValueError('Benchmark sample differs from model sample')
    if not model_pairs:
        return None
    if any(_number(m[1]) != _number(b[1]) for m, b in zip(model_pairs, benchmark_pairs)):
        raise ValueError('Benchmark realized values differ')
    denominator = mae(benchmark_pairs)
    return mae(model_pairs) / denominator if denominator else None


def _cutoff(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('as_of must be timezone-aware')
    return value.astimezone(timezone.utc)


def _observation_query(order):
    return f"""SELECT o.id, o.value, o.unit, o.vintage_id, v.known_at
        FROM observation o JOIN vintage v ON v.id=o.vintage_id
        WHERE o.indicator_id=s.indicator_id AND o.mode=s.mode
          AND o.reference_period=s.target_period AND v.known_at <= %(as_of)s
        ORDER BY v.known_at {order}, o.id {order} LIMIT 1"""


def _paired_rows(conn, as_of, mode, snapshot_id=None):
    # One SQL statement keeps both realized targets and all benchmark inputs on
    # the same MVCC snapshot, including when ingestion is committing concurrently.
    query = f"""SELECT s.*,
        f.id AS first_id, f.value AS first_value, f.unit AS first_unit,
        f.vintage_id AS first_vintage_id, f.known_at AS first_known_at,
        l.id AS latest_id, l.value AS latest_value, l.unit AS latest_unit,
        l.vintage_id AS latest_vintage_id, l.known_at AS latest_known_at
        FROM forecast_snapshot s
        LEFT JOIN LATERAL ({_observation_query('ASC')}) f ON true
        LEFT JOIN LATERAL ({_observation_query('DESC')}) l ON true
        WHERE s.mode=%(mode)s AND s.forecast_origin_at <= %(as_of)s
          AND s.created_at <= %(as_of)s
          AND (%(snapshot_id)s::text IS NULL OR s.id=%(snapshot_id)s)
        ORDER BY s.id"""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, dict(as_of=as_of, mode=mode, snapshot_id=snapshot_id))
        return cur.fetchall()


def _realized(row, target):
    prefix = 'first' if target == 'first_release' else 'latest'
    if row[f'{prefix}_id'] is None:
        return None
    # A later revision does not make an already-observed target ex-ante again.
    if row['first_known_at'] <= row['forecast_origin_at']:
        return None
    if row[f'{prefix}_unit'] != row['unit']:
        raise ValueError(f"Incompatible realized unit for snapshot {row['id']}")
    return dict(id=row[f'{prefix}_id'], value=row[f'{prefix}_value'],
                unit=row[f'{prefix}_unit'], vintage_id=row[f'{prefix}_vintage_id'],
                known_at=row[f'{prefix}_known_at'])


def match_realized(conn, snapshot, target, as_of):
    """Match a persisted snapshot to first/latest release, bounded by explicit as_of."""
    if target not in TARGETS:
        raise ValueError('Unknown realized target')
    rows = _paired_rows(conn, _cutoff(as_of), snapshot['mode'], snapshot['id'])
    return _realized(rows[0], target) if rows else None


def _canonical(value):
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if isinstance(value, (Decimal, uuid.UUID)):
        return str(value)
    return value


def _benchmark_key(row, target):
    return tuple(row[key] for key in ('indicator_id', 'target_period', 'forecast_origin_at',
                                     'horizon', 'unit', 'origin_kind', 'mode')) + (target,)


def run_backtest(conn, as_of, mode):
    """Evaluate frozen inputs atomically; same cutoff, inputs and code reuse a run.

    The explicit cutoff and minimum sample are hashed as evaluation parameters.
    Relative MAE requires a random-walk pair for every member of the model sample.
    Database errors propagate; callers keep control of their surrounding transaction.
    """
    as_of = _cutoff(as_of)
    if mode not in ('fixture', 'source'):
        raise ValueError('Unknown data mode')
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT clock_timestamp() AS now')
        if as_of > cur.fetchone()['now']:
            raise ValueError('as_of cannot be in the future')
        rows = _paired_rows(conn, as_of, mode)
        inputs_hash = fingerprint(_canonical(dict(as_of=as_of, mode=mode,
                                                min_sample=MIN_SAMPLE, snapshots=rows)))
        run_id = uuid.uuid4()
        cur.execute('''INSERT INTO backtest_run
            (id, inputs_hash, code_version, as_of, min_sample, mode)
            VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (inputs_hash,code_version)
            DO NOTHING RETURNING id''',
            (run_id, inputs_hash, CODE_VERSION, as_of, MIN_SAMPLE, mode))
        if cur.fetchone() is None:
            cur.execute('SELECT id,as_of FROM backtest_run WHERE inputs_hash=%s AND code_version=%s',
                        (inputs_hash, CODE_VERSION))
            existing = cur.fetchone()
            cur.execute('SELECT count(*) AS n FROM backtest_metric WHERE run_id=%s', (existing['id'],))
            return dict(run_id=str(existing['id']), as_of=existing['as_of'].isoformat(),
                        metrics=cur.fetchone()['n'], reused=True, mode=mode, experimental=True)

        groups, benchmarks = defaultdict(list), {}
        for row in rows:
            for target in TARGETS:
                actual = _realized(row, target)
                if actual is None:
                    continue
                if row['forecast_source'] == 'benchmark_random_walk':
                    key = _benchmark_key(row, target)
                    if key in benchmarks:
                        raise ValueError('Ambiguous random-walk versions for the same forecast origin')
                    benchmarks[key] = (row, actual)
                key = (row['indicator_id'], row['horizon'], row['forecast_source'], target, row['origin_kind'])
                groups[key].append((row, actual))

        for key, members in sorted(groups.items()):
            units = {row['unit'] for row, _ in members}
            if len(units) != 1:
                raise ValueError('Cannot aggregate incompatible units')
            pairs = [(row['point_value'], actual['value']) for row, actual in members]
            matched_model, matched_benchmark = [], []
            for row, actual in members:
                benchmark = benchmarks.get(_benchmark_key(row, key[3]))
                if benchmark is not None:
                    benchmark_row, benchmark_actual = benchmark
                    if benchmark_actual['id'] != actual['id']:
                        raise ValueError('Benchmark realized vintage differs')
                    matched_model.append((row['point_value'], actual['value']))
                    matched_benchmark.append((benchmark_row['point_value'], actual['value']))
            coverage = interval_coverage((row['lower_value'], row['upper_value'], actual['value'])
                                         for row, actual in members)
            cur.execute('''INSERT INTO backtest_metric
                (run_id,indicator_id,horizon,forecast_source,target,origin_kind,unit,n_obs,
                 mae,rmse,bias,interval_coverage,relative_mae_vs_rw,insufficient_sample)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (run_id, *key, next(iter(units)), len(pairs), mae(pairs), rmse(pairs), bias(pairs),
                 coverage, relative_mae(matched_model, matched_benchmark)
                 if len(matched_model) == len(pairs) else None, len(pairs) < MIN_SAMPLE))
        return dict(run_id=str(run_id), as_of=as_of.isoformat(), metrics=len(groups), reused=False,
                    mode=mode, experimental=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Experimental vintage-aware forecast backtesting')
    parser.add_argument('--as-of', required=True, type=datetime.fromisoformat)
    parser.add_argument('--mode', required=True, choices=('fixture', 'source'))
    args = parser.parse_args(argv)
    try:
        cutoff = _cutoff(args.as_of)
    except ValueError as exc:
        parser.error(str(exc))
    with psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row) as conn:
        result = run_backtest(conn, cutoff, args.mode)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
