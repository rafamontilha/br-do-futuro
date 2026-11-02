"""Freeze forecasts as append-only snapshots for later backtesting.

Spec: specs/2026-11-01-phase-1-forecast-backtesting/ (group 2).

Rules enforced here (in addition to the schema checks of db/009):
* A snapshot only uses information knowable at ``forecast_origin_at``.
* ``origin_kind = 'ex_ante'`` only for ``mode = 'source'`` forecasts whose realized value
  was not yet known at the origin; everything else (all fixtures) is ``reconstructed``.
* Trajectory intervals have no declared nominal level, so they are dropped instead of
  inventing one; the drop is reported in the returned stats.
* Database errors propagate; there is no static fallback.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from psycopg.rows import dict_row

from .catalog import INDICATORS
from .scenario import DEPENDENCIES, fingerprint

log = logging.getLogger(__name__)

RANDOM_WALK_VERSION = "random_walk-v1"
SEASONAL_NAIVE_VERSION = "seasonal_naive-v1"


# --------------------------------------------------------------------------- helpers

def add_months(value: date, months: int) -> date:
    """Shift a first-of-period date by whole months (day is clamped to 1)."""
    total = value.year * 12 + (value.month - 1) + months
    return date(total // 12, total % 12 + 1, 1)


def month_diff(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def compute_horizon(frequency: str, last_known_period: date, target_period: date) -> int:
    """Distance from the last period known at origin to the target, in native periods.

    May be negative (target already observed); callers decide whether to skip.
    """
    if frequency == "daily":
        return (target_period - last_known_period).days
    if frequency == "monthly":
        return month_diff(last_known_period, target_period)
    if frequency == "quarterly":
        months = month_diff(last_known_period, target_period)
        if months % 3:
            raise ValueError(f"Quarterly periods not aligned: {last_known_period} -> {target_period}")
        return months // 3
    if frequency == "annual":
        return target_period.year - last_known_period.year
    raise ValueError(f"Unknown frequency: {frequency}")


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("forecast_origin_at must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def snapshot_id(snap: Dict[str, Any]) -> str:
    return fingerprint(dict(
        indicator_id=snap["indicator_id"],
        target_period=snap["target_period"].isoformat(),
        forecast_origin_at=_utc_iso(snap["forecast_origin_at"]),
        forecast_source=snap["forecast_source"],
        model_version=snap["model_version"],
        mode=snap["mode"],
    ))


def _db_now(conn) -> datetime:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT clock_timestamp() AS now")
        return cur.fetchone()["now"]


def _realized_known(conn, indicator_id: str, target_period: date, mode: str, at: datetime) -> bool:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT 1 FROM observation o JOIN vintage v ON v.id = o.vintage_id
               WHERE o.indicator_id = %s AND o.mode = %s AND o.reference_period = %s
                 AND v.known_at <= %s LIMIT 1""",
            (indicator_id, mode, target_period, at),
        )
        return cur.fetchone() is not None


def _origin_kind(conn, mode: str, indicator_id: str, target_period: date, origin: datetime) -> str:
    if mode != "source":
        return "reconstructed"
    if _realized_known(conn, indicator_id, target_period, mode, origin):
        return "reconstructed"
    return "ex_ante"


_COLUMNS = (
    "id", "indicator_id", "target_period", "forecast_origin_at", "input_vintage_id", "horizon",
    "frequency", "forecast_source", "source_ref", "model_version", "point_value", "lower_value",
    "upper_value", "interval_level", "unit", "origin_kind", "mode",
)


def _insert_snapshot(conn, snap: Dict[str, Any]) -> bool:
    row = {k: snap.get(k) for k in _COLUMNS}
    row["id"] = snapshot_id(snap)
    snap["id"] = row["id"]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""INSERT INTO forecast_snapshot ({", ".join(_COLUMNS)})
                VALUES ({", ".join(f"%({c})s" for c in _COLUMNS)})
                ON CONFLICT DO NOTHING RETURNING id""",
            row,
        )
        return cur.fetchone() is not None


def _latest_observation(conn, indicator_id: str, mode: str, at: datetime,
                        reference_period: Optional[date] = None) -> Optional[Dict[str, Any]]:
    sql = """SELECT o.reference_period, o.value, o.unit, o.vintage_id
             FROM observation o JOIN vintage v ON v.id = o.vintage_id
             WHERE o.indicator_id = %s AND o.mode = %s AND v.known_at <= %s"""
    params: List[Any] = [indicator_id, mode, at]
    if reference_period is not None:
        sql += " AND o.reference_period = %s"
        params.append(reference_period)
    sql += " ORDER BY o.reference_period DESC, v.known_at DESC LIMIT 1"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchone()


# --------------------------------------------------------------------------- benchmarks

def compute_benchmark_snapshots(conn, snapshots: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Naive benchmarks paired with each forecast snapshot (same origin, target, horizon).

    Only observations with ``vintage.known_at <= forecast_origin_at`` are used.
    """
    inserted, skipped = 0, Counter()
    for snap in snapshots:
        origin = snap["forecast_origin_at"]
        last = _latest_observation(conn, snap["indicator_id"], snap["mode"], origin)
        if last is None:
            skipped["benchmark_no_observation_at_origin"] += 1
            continue
        if last["unit"] != snap["unit"]:
            skipped["benchmark_unit_mismatch"] += 1
            continue
        base = dict(
            indicator_id=snap["indicator_id"], target_period=snap["target_period"],
            forecast_origin_at=origin, horizon=snap["horizon"], frequency=snap["frequency"],
            source_ref=None, unit=snap["unit"], origin_kind=snap["origin_kind"], mode=snap["mode"],
        )
        rw = dict(base, forecast_source="benchmark_random_walk",
                  model_version=f"{RANDOM_WALK_VERSION}:{snap['frequency']}",
                  point_value=last["value"], input_vintage_id=last["vintage_id"])
        inserted += _insert_snapshot(conn, rw)

        if snap["frequency"] != "monthly":
            continue
        # y(T) = y(T - 12k) with the smallest k >= 1 that is already observed at origin.
        steps = max(1, -(-month_diff(last["reference_period"], snap["target_period"]) // 12))
        seasonal_period = add_months(snap["target_period"], -12 * steps)
        seasonal = _latest_observation(conn, snap["indicator_id"], snap["mode"], origin, seasonal_period)
        if seasonal is None:
            skipped["benchmark_seasonal_period_missing"] += 1
            continue
        if seasonal["unit"] != snap["unit"]:
            skipped["benchmark_unit_mismatch"] += 1
            continue
        sn = dict(base, forecast_source="benchmark_seasonal_naive",
                  model_version=f"{SEASONAL_NAIVE_VERSION}:monthly",
                  point_value=seasonal["value"], input_vintage_id=seasonal["vintage_id"])
        inserted += _insert_snapshot(conn, sn)
    return dict(inserted=inserted, skipped=dict(skipped))


# --------------------------------------------------------------------------- trajectories

def _capture_trajectory_snapshots(conn, as_of: datetime, mode: Optional[str] = None) -> Dict[str, Any]:
    """Freeze ``indicator_trajectories`` forecasts as known at ``as_of``.

    Only rows not updated after ``as_of`` are used (their value at ``as_of`` is certain);
    unchanged forecasts are not re-snapshotted.
    """
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if as_of > _db_now(conn):
        raise ValueError("as_of cannot be in the future")

    if mode not in (None, "fixture", "source"):
        raise ValueError("Unknown mode")
    sql = "SELECT * FROM indicator_trajectories"
    params: List[Any] = []
    if mode is not None:
        sql += " WHERE mode = %s"
        params.append(mode)
    sql += " ORDER BY indicator_id, mode, period_date"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    last_known: Dict[tuple, date] = {}
    for r in rows:
        valid = r["as_of_valid_until"]
        if r["actual_value"] is not None and (valid is None or valid <= as_of) and r["updated_at"] <= as_of:
            key = (r["indicator_id"], r["mode"])
            last_known[key] = max(last_known.get(key, r["period_date"]), r["period_date"])

    inserted, skipped, new = 0, Counter(), []
    for r in rows:
        if r["forecast_value"] is None:
            continue
        if r["updated_at"] > as_of:
            skipped["row_updated_after_as_of"] += 1
            continue
        meta = INDICATORS[r["indicator_id"]]
        if meta["unit"] != r["unit"]:
            raise ValueError(f"Trajectory unit mismatch: {r['id']}")
        observation = _latest_observation(conn, r["indicator_id"], r["mode"], as_of)
        last = observation["reference_period"] if observation else last_known.get((r["indicator_id"], r["mode"]))
        if observation and observation["unit"] != r["unit"]:
            raise ValueError(f"Observation unit mismatch: {r['id']}")
        if r["mode"] == "source" and observation is None:
            last = None
        if last is None:
            skipped["no_actual_known_at_origin"] += 1
            continue
        horizon = compute_horizon(meta["frequency"], last, r["period_date"])
        if horizon <= 0:
            continue  # target already observed at origin: not a forecast
        model_version = f"indicator_trajectories:{r['source_agency']}"
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """SELECT point_value FROM forecast_snapshot
                   WHERE forecast_source = 'trajectory' AND source_ref = %s AND mode = %s
                     AND model_version = %s AND forecast_origin_at <= %s
                   ORDER BY forecast_origin_at DESC LIMIT 1""",
                (r["id"], r["mode"], model_version, as_of),
            )
            previous = cur.fetchone()
        if previous is not None and Decimal(previous["point_value"]) == Decimal(r["forecast_value"]):
            skipped["unchanged"] += 1
            continue
        if r["forecast_lower"] is not None or r["forecast_upper"] is not None:
            skipped["interval_dropped_no_nominal_level"] += 1
        snap = dict(
            indicator_id=r["indicator_id"], target_period=r["period_date"], forecast_origin_at=as_of,
            input_vintage_id=observation["vintage_id"] if observation else None,
            horizon=horizon, frequency=meta["frequency"],
            forecast_source="trajectory", source_ref=r["id"], model_version=model_version,
            point_value=r["forecast_value"], lower_value=None, upper_value=None, interval_level=None,
            unit=r["unit"], mode=r["mode"],
            # Mutable trajectories do not prove a historical forecast origin.
            origin_kind="reconstructed",
        )
        if _insert_snapshot(conn, snap):
            inserted += 1
            new.append(snap)
    benchmarks = compute_benchmark_snapshots(conn, new)
    skipped.update(benchmarks["skipped"])
    result = dict(inserted=inserted, benchmarks_inserted=benchmarks["inserted"], skipped=dict(skipped))
    log.info("trajectory forecast snapshots captured: %s", result)
    return result


# --------------------------------------------------------------------------- scenario runs

def _scenario_indicator(scenario_id: str) -> str:
    matches = [ind for ind, scenarios in DEPENDENCIES.items() if scenario_id in scenarios]
    if len(matches) != 1:
        raise ValueError(f"Cannot resolve forecast indicator for scenario {scenario_id!r}")
    return matches[0]


def _capture_scenario_snapshots(conn, scenario_run_id: str) -> Dict[str, Any]:
    """Freeze the projected path of one ``scenario_run`` (origin = run creation time)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT id, scenario_id, model_version, inputs, outputs, mode, created_at
               FROM scenario_run WHERE id = %s""",
            (scenario_run_id,),
        )
        run = cur.fetchone()
    if run is None:
        raise ValueError(f"scenario_run not found: {scenario_run_id}")
    inputs = run["inputs"] or {}
    for key in ("reference_period", "vintage_id"):
        if not inputs.get(key):
            raise ValueError(f"scenario_run {scenario_run_id} inputs missing {key!r}")
    indicator_id = _scenario_indicator(run["scenario_id"])
    meta = INDICATORS[indicator_id]
    if meta["frequency"] != "monthly":
        raise ValueError(f"Scenario snapshots assume a monthly base series, got {meta['frequency']}")
    base_period = date.fromisoformat(inputs["reference_period"])
    origin = run["created_at"]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""SELECT o.reference_period, o.unit, v.known_at FROM observation o
                       JOIN vintage v ON v.id=o.vintage_id
                       WHERE o.vintage_id=%s AND o.indicator_id=%s AND o.mode=%s
                         AND o.reference_period=%s""",
                    (inputs["vintage_id"], indicator_id, run["mode"], base_period))
        dependency = cur.fetchone()
    if dependency is None or dependency["known_at"] > origin or dependency["unit"] != meta["unit"]:
        raise ValueError("Scenario input vintage unavailable or incompatible at origin")
    last = _latest_observation(conn, indicator_id, run["mode"], origin)
    if last is None or last["unit"] != meta["unit"]:
        raise ValueError("Latest scenario observation unavailable or incompatible at origin")
    value_key = "debt_pct_gdp"

    inserted, new, skipped = 0, [], Counter()
    for step in run["outputs"]:
        years = int(step["horizon_years"])
        if years < 1 or Decimal(str(step["horizon_years"])) != years or value_key not in step:
            raise ValueError(f"Malformed scenario output in {scenario_run_id}: {step}")
        target = add_months(base_period, 12 * years)
        # Queue lag can make the scenario base older than the knowledge at creation.
        # Preserve its projected target, but measure horizon at the recorded origin.
        horizon = compute_horizon(meta["frequency"], last["reference_period"], target)
        if horizon <= 0:
            skipped["target_not_after_latest_known_period"] += 1
            continue
        snap = dict(
            indicator_id=indicator_id, target_period=target, forecast_origin_at=origin,
            input_vintage_id=inputs["vintage_id"], horizon=horizon, frequency=meta["frequency"],
            forecast_source="scenario_run", source_ref=run["id"],
            model_version=f"{run['model_version']}:{run['scenario_id']}",
            point_value=Decimal(str(step[value_key])), lower_value=None, upper_value=None,
            interval_level=None, unit=meta["unit"], mode=run["mode"],
            origin_kind=_origin_kind(conn, run["mode"], indicator_id, target, origin),
        )
        if _insert_snapshot(conn, snap):
            inserted += 1
            new.append(snap)
    benchmarks = compute_benchmark_snapshots(conn, new)
    skipped.update(benchmarks["skipped"])
    return dict(inserted=inserted, benchmarks_inserted=benchmarks["inserted"], skipped=dict(skipped))


def capture_trajectory_snapshots(conn, as_of: datetime, mode: Optional[str] = None) -> Dict[str, Any]:
    """Capture mutable trajectories conservatively as reconstructed, atomically.

    Horizons use the catalog's native frequency, even for year-end targets.
    No historical ex-ante provenance is inferred from mutable row timestamps.
    """
    with conn.transaction():
        return _capture_trajectory_snapshots(conn, as_of, mode)


def capture_scenario_snapshots(conn, scenario_run_id: str) -> Dict[str, Any]:
    """Capture immutable run outputs and their benchmarks in the caller transaction."""
    with conn.transaction():
        return _capture_scenario_snapshots(conn, scenario_run_id)
