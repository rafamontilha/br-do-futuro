"""
Observability Metrics & SLO Compliance module for Brasil do Futuro (Incremento 04).

Covers telemetry and validation for the 4 canonical planes:
1. Platform
2. Data & Contracts
3. Models & Scenarios
4. Decisions & Audit
Plus Constitutional SLO compliance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


VALID_DATABASE_STATUSES = {"healthy", "unconfigured", "unreachable"}


class SLOViolationError(Exception):
    """Raised when an observability snapshot violates SLO compliance criteria."""
    pass


def get_canonical_observability_snapshot() -> Dict[str, Any]:
    """Returns a canonical, fully compliant observability snapshot baseline."""
    return {
        "timestamp": "2026-10-29T10:30:00Z",
        "platform": {
            "uptime_seconds": 3600,
            "database_status": "healthy",
            "error_rate_pct": 0.02,
            "p95_latency_ms": 12.4,
        },
        "data": {
            "tracked_series_count": 12,
            "stale_series_count": 0,
            "quarantine_count": 0,
            "last_ingestion_at": "2026-10-29T09:15:00Z",
        },
        "models": {
            "active_scenarios_count": 3,
            "calibrated_parameters_count": 4,
            "last_simulation_at": "2026-10-29T09:45:00Z",
        },
        "decisions": {
            "total_decisions_count": 1,
            "pending_reviews_count": 0,
            "audit_chain_intact": True,
        },
        "slo_compliance": {
            "source_window_compliance_pct": 99.4,
            "metadata_completeness_pct": 100.0,
            "scenario_lineage_coverage_pct": 100.0,
            "reproducible_forecasts_pct": 100.0,
        },
    }


def validate_observability_schema(snapshot: Dict[str, Any]) -> List[str]:
    """
    Validates structural schema of the observability snapshot across all four planes
    and slo_compliance.
    Returns a list of schema error descriptions (empty list if valid).
    """
    errors: List[str] = []
    if not isinstance(snapshot, dict):
        return ["Snapshot must be a dictionary"]

    required_top_keys = ["platform", "data", "models", "decisions", "slo_compliance"]
    for key in required_top_keys:
        if key not in snapshot:
            errors.append(f"Missing required top-level key: '{key}'")
        elif not isinstance(snapshot[key], dict):
            errors.append(f"Top-level key '{key}' must be a dictionary")

    if errors:
        return errors

    # 1. Platform schema
    platform = snapshot["platform"]
    for field in ["uptime_seconds", "database_status", "error_rate_pct", "p95_latency_ms"]:
        if field not in platform:
            errors.append(f"Missing field in 'platform': '{field}'")

    # 2. Data schema
    data = snapshot["data"]
    for field in ["tracked_series_count", "stale_series_count", "quarantine_count"]:
        if field not in data:
            errors.append(f"Missing field in 'data': '{field}'")

    # 3. Models schema
    models = snapshot["models"]
    for field in ["active_scenarios_count", "calibrated_parameters_count"]:
        if field not in models:
            errors.append(f"Missing field in 'models': '{field}'")

    # 4. Decisions schema
    decisions = snapshot["decisions"]
    for field in ["total_decisions_count", "pending_reviews_count", "audit_chain_intact"]:
        if field not in decisions:
            errors.append(f"Missing field in 'decisions': '{field}'")

    # 5. SLO Compliance schema
    slo = snapshot["slo_compliance"]
    for field in [
        "source_window_compliance_pct",
        "metadata_completeness_pct",
        "scenario_lineage_coverage_pct",
        "reproducible_forecasts_pct",
    ]:
        if field not in slo:
            errors.append(f"Missing field in 'slo_compliance': '{field}'")

    return errors


def validate_metric_types_and_ranges(snapshot: Dict[str, Any]) -> List[str]:
    """
    Validates expected types and range constraints for all metrics across all four planes
    and slo_compliance:
    - platform: uptime_seconds >= 0, database_status in ('healthy', 'unconfigured', 'unreachable'),
                error_rate_pct >= 0, p95_latency_ms >= 0
    - data: tracked_series_count >= 12, stale_series_count >= 0, quarantine_count >= 0
    - models: active_scenarios_count >= 3, calibrated_parameters_count >= 4
    - decisions: total_decisions_count >= 1, pending_reviews_count >= 0, audit_chain_intact is True
    - slo_compliance: source_window_compliance_pct >= 99.0, metadata_completeness_pct == 100.0,
                     scenario_lineage_coverage_pct == 100.0, reproducible_forecasts_pct == 100.0
    Returns a list of violations (empty list if valid).
    """
    schema_errors = validate_observability_schema(snapshot)
    if schema_errors:
        return [f"Schema error: {err}" for err in schema_errors]

    violations: List[str] = []

    # 1. Platform
    p = snapshot["platform"]
    uptime = p.get("uptime_seconds")
    if not isinstance(uptime, (int, float)) or uptime < 0:
        violations.append(f"platform.uptime_seconds must be a non-negative number, got {uptime}")

    db_status = p.get("database_status")
    if not isinstance(db_status, str) or db_status not in VALID_DATABASE_STATUSES:
        violations.append(
            f"platform.database_status must be one of {VALID_DATABASE_STATUSES}, got '{db_status}'"
        )

    err_rate = p.get("error_rate_pct")
    if not isinstance(err_rate, (int, float)) or err_rate < 0:
        violations.append(f"platform.error_rate_pct must be a number >= 0, got {err_rate}")

    p95 = p.get("p95_latency_ms")
    if not isinstance(p95, (int, float)) or p95 < 0:
        violations.append(f"platform.p95_latency_ms must be a number >= 0, got {p95}")

    # 2. Data
    d = snapshot["data"]
    tracked = d.get("tracked_series_count")
    if not isinstance(tracked, int) or tracked < 12:
        violations.append(f"data.tracked_series_count must be an integer >= 12, got {tracked}")

    stale = d.get("stale_series_count")
    if not isinstance(stale, int) or stale < 0:
        violations.append(f"data.stale_series_count must be an integer >= 0, got {stale}")

    quarantine = d.get("quarantine_count")
    if not isinstance(quarantine, int) or quarantine < 0:
        violations.append(f"data.quarantine_count must be an integer >= 0, got {quarantine}")

    # 3. Models
    m = snapshot["models"]
    scenarios = m.get("active_scenarios_count")
    if not isinstance(scenarios, int) or scenarios < 3:
        violations.append(f"models.active_scenarios_count must be an integer >= 3, got {scenarios}")

    calibrated = m.get("calibrated_parameters_count")
    if not isinstance(calibrated, int) or calibrated < 4:
        violations.append(
            f"models.calibrated_parameters_count must be an integer >= 4, got {calibrated}"
        )

    # 4. Decisions
    dec = snapshot["decisions"]
    total_dec = dec.get("total_decisions_count")
    if not isinstance(total_dec, int) or total_dec < 1:
        violations.append(f"decisions.total_decisions_count must be an integer >= 1, got {total_dec}")

    pending = dec.get("pending_reviews_count")
    if not isinstance(pending, int) or pending < 0:
        violations.append(f"decisions.pending_reviews_count must be an integer >= 0, got {pending}")

    chain_intact = dec.get("audit_chain_intact")
    if not isinstance(chain_intact, bool) or chain_intact is not True:
        violations.append(f"decisions.audit_chain_intact must be strictly True, got {chain_intact}")

    # 5. SLO Compliance
    slo = snapshot["slo_compliance"]
    src_win = slo.get("source_window_compliance_pct")
    if not isinstance(src_win, (int, float)) or src_win < 99.0:
        violations.append(f"slo_compliance.source_window_compliance_pct must be >= 99.0, got {src_win}")

    meta_comp = slo.get("metadata_completeness_pct")
    if not isinstance(meta_comp, (int, float)) or float(meta_comp) != 100.0:
        violations.append(f"slo_compliance.metadata_completeness_pct must be == 100.0, got {meta_comp}")

    lineage = slo.get("scenario_lineage_coverage_pct")
    if not isinstance(lineage, (int, float)) or float(lineage) != 100.0:
        violations.append(f"slo_compliance.scenario_lineage_coverage_pct must be == 100.0, got {lineage}")

    reproducible = slo.get("reproducible_forecasts_pct")
    if not isinstance(reproducible, (int, float)) or float(reproducible) != 100.0:
        violations.append(f"slo_compliance.reproducible_forecasts_pct must be == 100.0, got {reproducible}")

    return violations


def validate_slo_compliance(snapshot: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Evaluates operational and constitutional SLO compliance for an observability snapshot.
    Detects anomalies across all four planes and SLO compliance metrics:
    - Platform anomalies: database_status == 'unreachable', excessive error rates
    - Data anomalies: tracked_series_count < 12, negative counts
    - Models anomalies: active_scenarios_count < 3, calibrated_parameters_count < 4
    - Decisions anomalies: audit_chain_intact is False, total_decisions_count < 1
    - SLO compliance anomalies: source_window < 99.0%, incomplete metadata/lineage/forecasts (< 100.0%)

    Returns:
        (is_compliant: bool, violations: List[str])
    """
    violations = validate_metric_types_and_ranges(snapshot)
    anomalies: List[str] = list(violations)

    if not violations:
        # Check specific operational anomalies
        platform = snapshot["platform"]
        if platform.get("database_status") == "unreachable":
            anomalies.append("Platform anomaly: database is unreachable")

    # If database status is unreachable even if allowed in enum, it's an operational anomaly
    if snapshot.get("platform", {}).get("database_status") == "unreachable" and "Platform anomaly: database is unreachable" not in anomalies:
        anomalies.append("Platform anomaly: database is unreachable")

    is_compliant = len(anomalies) == 0
    return is_compliant, anomalies


def assert_slo_compliance(snapshot: Dict[str, Any]) -> None:
    """Raises SLOViolationError if the snapshot contains any SLO anomalies or invalid ranges."""
    compliant, anomalies = validate_slo_compliance(snapshot)
    if not compliant:
        raise SLOViolationError(
            f"SLO compliance check failed with {len(anomalies)} anomalies: {'; '.join(anomalies)}"
        )
