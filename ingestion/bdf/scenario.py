"""Conditional accounting exercise, never a calibrated forecast or policy advice."""
import hashlib
import json
from decimal import Decimal

MODEL_VERSION = "fiscal-identity-v1"
SCENARIOS = {
    "continuity": dict(interest="0.10", growth="0.06", primary="0.00", adjustment="0.00"),
    "alternative": dict(interest="0.10", growth="0.06", primary="0.01", adjustment="0.00"),
    "adverse": dict(interest="0.12", growth="0.03", primary="-0.01", adjustment="0.01"),
}
# Only debt feeds this demonstration. Daily Selic is NOT effective annual debt interest.
DEPENDENCIES = {"br.debt.gross_pct_gdp": list(SCENARIOS)}


def validate_assumptions(assumptions):
    required = ("interest", "growth", "primary")
    for key in required:
        if key not in assumptions:
            raise ValueError(f"Missing required fiscal assumption: {key}")
    a = {}
    for key in ("interest", "growth", "primary", "adjustment"):
        val = assumptions.get(key, "0.00")
        try:
            dec = Decimal(str(val))
        except Exception as exc:
            raise ValueError(f"Invalid decimal for assumption {key}: {val}") from exc
        if not dec.is_finite():
            raise ValueError(f"Non-finite assumption {key}: {val}")
        a[key] = dec
    if a["growth"] <= Decimal("-1"):
        raise ValueError("Growth rate must be strictly greater than -100%")
    horizon = int(assumptions.get("horizon_years", 4))
    if horizon < 1 or horizon > 20:
        raise ValueError("Horizon years must be between 1 and 20")
    return a, horizon


def fiscal_path(debt_pct, assumptions, years=4):
    try:
        debt = Decimal(str(debt_pct)) / 100
    except Exception as exc:
        raise ValueError(f"Invalid base debt percentage: {debt_pct}") from exc
    if not debt.is_finite() or debt < 0:
        raise ValueError("Base debt percentage must be finite and non-negative")
    a, horizon = validate_assumptions(assumptions)
    if "horizon_years" not in assumptions:
        horizon = int(years)
    result = []
    for step in range(1, horizon + 1):
        debt = (1 + a["interest"]) / (1 + a["growth"]) * debt - a["primary"] + a["adjustment"]
        result.append(dict(horizon_years=step, debt_pct_gdp=str(debt * 100)))
    return result


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
