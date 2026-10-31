"""Multi-level materiality assessment and impact evaluation."""
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple


def evaluate_materiality(
    current_outputs: list,
    previous_outputs: Optional[list],
    scenario_id: str,
    threshold: Decimal = Decimal("0.50"),
    target_cap: Optional[Decimal] = Decimal("80.00")
) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluates whether a model recalculation produces a material impact.
    Criteria:
      1. Absolute delta: |current - previous| >= threshold on final horizon.
      2. Target breach: current trajectory breaches institutional target/cap.
    """
    if not current_outputs:
        return False, {"reason": "no_current_outputs"}

    curr_val = Decimal(str(current_outputs[-1]["debt_pct_gdp"]))
    
    delta_pp: Optional[Decimal] = None
    delta_material = False
    if previous_outputs and len(previous_outputs) > 0:
        prev_val = Decimal(str(previous_outputs[-1]["debt_pct_gdp"]))
        delta_pp = curr_val - prev_val
        if abs(delta_pp) >= threshold:
            delta_material = True

    # Target breach check
    target_breach = False
    if target_cap is not None and curr_val > target_cap:
        # If debt exceeds cap or deteriorates further
        target_breach = True

    is_material = delta_material or target_breach

    if delta_material and target_breach:
        rule = "composite_materiality_v1"
    elif delta_material:
        rule = "delta_absolute"
    elif target_breach:
        rule = "target_breach"
    else:
        rule = "immaterial"

    evidence = {
        "scenario_id": scenario_id,
        "current_debt_pct": str(curr_val),
        "delta_pp": str(delta_pp) if delta_pp is not None else "0.00",
        "threshold_pp": str(threshold),
        "target_breach": target_breach,
        "target_cap": str(target_cap) if target_cap is not None else None,
        "rule": rule,
        "classification": "hypothetical",
        "publication_allowed": not is_material
    }

    return is_material, evidence
