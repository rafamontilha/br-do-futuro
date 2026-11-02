"""Schema-level guarantees of migration 009 (forecast snapshots and backtesting).

Runs against the dedicated ``bdf_test`` database only (see ``conftest.db``).
Connections use ``dict_row`` to match the worker daemons' runtime configuration.
"""
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

ORIGIN = datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc)


def _snapshot(**overrides):
    row = {
        "id": "snap-" + uuid.uuid4().hex[:12],
        "indicator_id": "br.ipca.12m",
        "target_period": "2025-12-01",
        "forecast_origin_at": ORIGIN,
        "horizon": 11,
        "frequency": "monthly",
        "forecast_source": "trajectory",
        "source_ref": "traj-ipca-2025",
        "model_version": "test-v1",
        "point_value": 3.9,
        "lower_value": 3.2,
        "upper_value": 4.6,
        "interval_level": 0.8,
        "unit": "percent_year",
        "origin_kind": "reconstructed",
        "mode": "fixture",
    }
    row.update(overrides)
    return row


def _insert_snapshot(conn, row):
    cols = ", ".join(row)
    params = ", ".join(f"%({k})s" for k in row)
    conn.execute(f"INSERT INTO forecast_snapshot ({cols}) VALUES ({params})", row)


def _insert_run(conn, **overrides):
    row = {
        "id": uuid.uuid4(),
        "inputs_hash": "hash-" + uuid.uuid4().hex,
        "code_version": "backtest-test-v1",
        "as_of": ORIGIN,
        "min_sample": 8,
        "mode": "fixture",
    }
    row.update(overrides)
    conn.execute(
        "INSERT INTO backtest_run (id, inputs_hash, code_version, as_of, min_sample, mode) "
        "VALUES (%(id)s, %(inputs_hash)s, %(code_version)s, %(as_of)s, %(min_sample)s, %(mode)s)",
        row,
    )
    return row


def _insert_metric(conn, run_id, **overrides):
    row = {
        "run_id": run_id,
        "indicator_id": "br.ipca.12m",
        "horizon": 1,
        "forecast_source": "trajectory",
        "target": "first_release",
        "origin_kind": "reconstructed",
        "unit": "percent_year",
        "n_obs": 3,
        "mae": 0.4,
        "rmse": 0.5,
        "bias": -0.1,
        "interval_coverage": None,
        "relative_mae_vs_rw": None,
        "insufficient_sample": True,
    }
    row.update(overrides)
    cols = ", ".join(row)
    params = ", ".join(f"%({k})s" for k in row)
    conn.execute(f"INSERT INTO backtest_metric ({cols}) VALUES ({params})", row)


def test_migration_is_idempotent(db):
    with psycopg.connect(db) as conn:
        conn.execute(Path("db/009_forecast_backtesting.sql").read_text())
        conn.execute(Path("db/009_forecast_backtesting.sql").read_text())
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT tgname FROM pg_trigger WHERE tgname IN "
                "('immutable_forecast_snapshot','immutable_backtest_run','immutable_backtest_metric')"
            )
            assert {r["tgname"] for r in cur.fetchall()} == {
                "immutable_forecast_snapshot",
                "immutable_backtest_run",
                "immutable_backtest_metric",
            }


def test_no_seed_rows_are_created(db):
    with psycopg.connect(db) as conn, conn.cursor(row_factory=dict_row) as cur:
        for table in ("forecast_snapshot", "backtest_run", "backtest_metric"):
            cur.execute(f"SELECT count(*) AS n FROM {table}")
            assert cur.fetchone()["n"] == 0, f"{table} must not be seeded with invented values"


@pytest.mark.parametrize("table", ["forecast_snapshot", "backtest_run", "backtest_metric"])
def test_tables_are_append_only(db, table):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        _insert_snapshot(conn, _snapshot(id="snap-immutable"))
        run = _insert_run(conn)
        _insert_metric(conn, run["id"])
        conn.commit()
        statements = {
            "forecast_snapshot": ("UPDATE forecast_snapshot SET point_value = 0", "DELETE FROM forecast_snapshot"),
            "backtest_run": ("UPDATE backtest_run SET min_sample = 1", "DELETE FROM backtest_run"),
            "backtest_metric": ("UPDATE backtest_metric SET mae = 0", "DELETE FROM backtest_metric"),
        }[table]
        for sql in statements:
            with pytest.raises(psycopg.errors.RaiseException, match="append-only evidence"):
                conn.execute(sql)
            conn.rollback()


def test_valid_snapshot_without_interval_is_accepted(db):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        _insert_snapshot(
            conn,
            _snapshot(lower_value=None, upper_value=None, interval_level=None, origin_kind="ex_ante"),
        )
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT origin_kind, created_at FROM forecast_snapshot")
            row = cur.fetchone()
        assert row["origin_kind"] == "ex_ante"
        assert row["created_at"] >= ORIGIN


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"upper_value": None}, id="half-interval"),
        pytest.param({"interval_level": None}, id="interval-without-level"),
        pytest.param({"interval_level": 1.0}, id="interval-level-out-of-range"),
        pytest.param({"lower_value": 4.0}, id="point-below-lower"),
        pytest.param({"forecast_origin_at": datetime.now(timezone.utc) + timedelta(days=1)}, id="future-origin"),
        pytest.param({"horizon": -1}, id="negative-horizon"),
        pytest.param({"origin_kind": "ex_post"}, id="unknown-origin-kind"),
        pytest.param({"mode": "official"}, id="unknown-mode"),
        pytest.param({"forecast_source": "focus"}, id="unknown-source"),
        pytest.param({"forecast_source": "benchmark_random_walk"}, id="benchmark-with-source-ref"),
        pytest.param(
            {"forecast_source": "benchmark_seasonal_naive", "source_ref": None, "frequency": "daily"},
            id="seasonal-naive-non-monthly",
        ),
    ],
)
def test_invalid_snapshots_are_rejected(db, overrides):
    with psycopg.connect(db) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            _insert_snapshot(conn, _snapshot(**overrides))


def test_snapshot_natural_key_is_unique(db):
    with psycopg.connect(db) as conn:
        _insert_snapshot(conn, _snapshot(id="snap-a"))
        with pytest.raises(psycopg.errors.UniqueViolation):
            _insert_snapshot(conn, _snapshot(id="snap-b"))


def test_snapshot_input_vintage_must_exist(db):
    with psycopg.connect(db) as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            _insert_snapshot(conn, _snapshot(input_vintage_id=uuid.uuid4()))


def test_backtest_run_is_idempotent_by_inputs_hash_and_code_version(db):
    with psycopg.connect(db) as conn:
        _insert_run(conn, inputs_hash="same-hash", code_version="v1")
        _insert_run(conn, inputs_hash="same-hash", code_version="v2")
        with pytest.raises(psycopg.errors.UniqueViolation):
            _insert_run(conn, inputs_hash="same-hash", code_version="v1")


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"n_obs": 0}, id="empty-sample"),
        pytest.param({"mae": -0.1}, id="negative-mae"),
        pytest.param({"interval_coverage": 1.2}, id="coverage-above-one"),
        pytest.param({"target": "revised"}, id="unknown-target"),
        pytest.param({"relative_mae_vs_rw": -1}, id="negative-relative-mae"),
    ],
)
def test_invalid_metrics_are_rejected(db, overrides):
    with psycopg.connect(db) as conn:
        run = _insert_run(conn)
        with pytest.raises(psycopg.errors.CheckViolation):
            _insert_metric(conn, run["id"], **overrides)


def test_ex_ante_and_reconstructed_metrics_coexist_separately(db):
    with psycopg.connect(db) as conn:
        run = _insert_run(conn)
        _insert_metric(conn, run["id"], origin_kind="ex_ante")
        _insert_metric(conn, run["id"], origin_kind="reconstructed")
        with pytest.raises(psycopg.errors.UniqueViolation):
            _insert_metric(conn, run["id"], origin_kind="ex_ante")
