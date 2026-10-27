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


def fiscal_path(debt_pct, assumptions, years=4):
    debt = Decimal(str(debt_pct)) / 100
    a = {key: Decimal(value) for key, value in assumptions.items()}
    if not all(v.is_finite() for v in [debt, *a.values()]) or a["growth"] <= -1:
        raise ValueError("Invalid fiscal assumptions")
    result = []
    for step in range(1, years + 1):
        debt = (1 + a["interest"]) / (1 + a["growth"]) * debt - a["primary"] + a["adjustment"]
        result.append(dict(horizon_years=step, debt_pct_gdp=str(debt * 100)))
    return result


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
