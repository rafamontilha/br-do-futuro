"""Database-backed local queue; transaction makes acknowledgement and output atomic."""
import logging
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from opentelemetry import trace

import uuid
from .scenario import SCENARIOS, MODEL_VERSION, fiscal_path, fingerprint
from .dependency_engine import resolve_recalculation_plan
from .materiality import evaluate_materiality


def process_event(conn, event):
    p = event["payload"]
    if event["event_type"] == "DynamicSimulationRequested":
        sim_id = p["simulation_id"]
        base_debt = p["base_debt_pct"]
        assumptions = p["assumptions"]
        try:
            trajectory = fiscal_path(base_debt, assumptions)
            conn.execute("""UPDATE dynamic_simulations
                SET results=%s, status='completed', error=NULL, completed_at=clock_timestamp()
                WHERE simulation_id=%s""",
                (Jsonb(trajectory), sim_id))
        except (ValueError, ArithmeticError) as exc:
            conn.execute("""UPDATE dynamic_simulations
                SET error=%s, status='failed', completed_at=clock_timestamp()
                WHERE simulation_id=%s""",
                (str(exc), sim_id))
        return

    if event["event_type"] == "OutboxReplayRequested":
        from .freshness import execute_outbox_replay
        reason = p.get("reason", "Operator replay")
        user = p.get("triggered_by", "operator")
        filter_ind = p.get("filter_indicator_id")
        filter_type = p.get("filter_event_type")
        execute_outbox_replay(conn, reason=reason, triggered_by=user, filter_indicator_id=filter_ind, filter_event_type=filter_type)
        return

    if event["event_type"] not in ("EconomicIndicatorUpdated", "HistoricalSeriesRevised"):
        return

    # 1. Resolve DAG dependency plan and selective recalculation scope
    plan = resolve_recalculation_plan(conn, event)
    affected_scenario_ids = []
    if p["indicator_id"] == "br.debt.gross_pct_gdp":
        affected_scenario_ids = [
            node["node_id"].split(":", 1)[1]
            for node in plan.get("affected_nodes", [])
            if node["node_id"].startswith("scenario:") and node["node_id"].split(":", 1)[1] in SCENARIOS
        ]

    for scenario_id in affected_scenario_ids:
        # Only information already visible at this event's ingestion time may be used.
        # Base debt always comes from br.debt.gross_pct_gdp.
        observation = conn.execute("""SELECT o.*,v.known_at FROM observation o
            JOIN vintage v ON v.id=o.vintage_id WHERE indicator_id='br.debt.gross_pct_gdp' AND mode=%s
            AND v.known_at <= (SELECT known_at FROM vintage WHERE id=%s)
            ORDER BY reference_period DESC,v.known_at DESC LIMIT 1""",
            (p["mode"], p["vintage_id"])).fetchone()
        if not observation:
            raise ValueError("Missing scenario dependency")
        inputs = dict(observation_id=str(observation["id"]), vintage_id=str(observation["vintage_id"]),
            reference_period=observation["reference_period"].isoformat(), debt_pct_gdp=str(observation["value"]),
            assumptions=SCENARIOS[scenario_id], model_version=MODEL_VERSION, mode=p["mode"],
            classification="hypothetical", limitations="Uncalibrated accounting identity; assumptions are illustrative.")
        run_id = fingerprint(dict(scenario=scenario_id, **inputs))
        if conn.execute("SELECT 1 FROM scenario_run WHERE id=%s", (run_id,)).fetchone():
            continue
        outputs = fiscal_path(observation["value"], SCENARIOS[scenario_id])
        previous = conn.execute("""SELECT outputs FROM scenario_run WHERE scenario_id=%s AND mode=%s
            ORDER BY created_at DESC LIMIT 1""", (scenario_id, p["mode"])).fetchone()
        conn.execute("""INSERT INTO scenario_run(id,scenario_id,model_version,inputs,outputs,event_id,mode)
            VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (run_id, scenario_id, MODEL_VERSION, Jsonb(inputs), Jsonb(outputs), event["id"], p["mode"]))

        # 2. Evaluate multi-level materiality rules (delta and target breach).
        # Even without previous outputs (initial run), target breach (debt > 80%) is evaluated.
        prev_outputs = previous["outputs"] if previous else None
        base_debt_val = Decimal(str(observation["value"]))
        is_material, evidence = evaluate_materiality(
            current_outputs=outputs,
            previous_outputs=prev_outputs,
            scenario_id=scenario_id,
            threshold=Decimal("0.50"),
            target_cap=Decimal("80.00"),
            base_debt=base_debt_val
        )
        evidence["event_id"] = str(event["id"])
        evidence["mode"] = p["mode"]

        if is_material:
            alert_id = fingerprint(dict(run_id=run_id, rule=evidence["rule"]))
            conn.execute("""INSERT INTO alert(id, scenario_run_id, severity, owner_role, sla_hours, status, review_status, evidence)
                VALUES (%s, %s, 'material', 'Independent Reviewer', 48, 'new', 'pending_human_review', %s)
                ON CONFLICT (id) DO UPDATE SET evidence=EXCLUDED.evidence""",
                (alert_id, run_id, Jsonb(evidence)))

            # Emit MaterialReviewRequired event to outbox (recorded as processed domain event)
            conn.execute("""INSERT INTO outbox (id, event_type, payload, status, processed_at)
                VALUES (%s, 'MaterialReviewRequired', %s, 'processed', clock_timestamp())""",
                (uuid.uuid4(), Jsonb({"alert_id": alert_id, "scenario_run_id": run_id, "evidence": evidence, "mode": p["mode"]})))

        # Emit ScenarioRecalculated event to outbox (recorded as processed domain event)
        conn.execute("""INSERT INTO outbox (id, event_type, payload, status, processed_at)
            VALUES (%s, 'ScenarioRecalculated', %s, 'processed', clock_timestamp())""",
            (uuid.uuid4(), Jsonb({"scenario_run_id": run_id, "scenario_id": scenario_id, "mode": p["mode"], "is_material": is_material})))

    # 3. Guidance Target Materiality Assessment (for direct indicator targets like IPCA and Selic)
    affected_targets = []
    if p["indicator_id"] in ("br.ipca.12m", "br.selic.target_annual"):
        affected_targets = [
            node for node in plan.get("affected_nodes", [])
            if node.get("node_id", "").startswith("guidance_target:")
        ]
    for target in affected_targets:
        target_id = target["node_id"]
        if p.get("observation_id"):
            curr_obs = conn.execute("""SELECT o.*, v.known_at FROM observation o
                JOIN vintage v ON v.id=o.vintage_id WHERE o.id=%s""",
                (p["observation_id"],)).fetchone()
        elif p.get("reference_period"):
            curr_obs = conn.execute("""SELECT o.*, v.known_at FROM observation o
                JOIN vintage v ON v.id=o.vintage_id WHERE o.indicator_id=%s AND o.mode=%s
                AND v.id=%s AND o.reference_period=%s LIMIT 1""",
                (p["indicator_id"], p["mode"], p["vintage_id"], p["reference_period"])).fetchone()
        else:
            curr_obs = conn.execute("""SELECT o.*, v.known_at FROM observation o
                JOIN vintage v ON v.id=o.vintage_id WHERE o.indicator_id=%s AND o.mode=%s
                AND v.id=%s ORDER BY o.reference_period DESC LIMIT 1""",
                (p["indicator_id"], p["mode"], p["vintage_id"])).fetchone()
        if not curr_obs:
            continue

        latest_series_obs = conn.execute("""SELECT o.*, v.known_at FROM observation o
            JOIN vintage v ON v.id=o.vintage_id WHERE o.indicator_id=%s AND o.mode=%s
            AND v.known_at <= %s
            ORDER BY o.reference_period DESC, v.known_at DESC LIMIT 1""",
            (p["indicator_id"], p["mode"], curr_obs["known_at"])).fetchone()
        is_latest_period = bool(
            latest_series_obs
            and curr_obs["reference_period"] == latest_series_obs["reference_period"]
        )

        # First check for a prior vintage of the exact same reference_period (historical revision)
        prev_obs = conn.execute("""SELECT o.*, v.known_at FROM observation o
            JOIN vintage v ON v.id=o.vintage_id WHERE o.indicator_id=%s AND o.mode=%s
            AND o.reference_period=%s AND v.known_at < %s
            ORDER BY v.known_at DESC LIMIT 1""",
            (p["indicator_id"], p["mode"], curr_obs["reference_period"], curr_obs["known_at"])).fetchone()

        # If this is a newly released latest reference_period from a subsequent vintage,
        # compare against the immediately preceding reference_period from prior vintages.
        if prev_obs is None and is_latest_period:
            prev_obs = conn.execute("""SELECT o.*, v.known_at FROM observation o
                JOIN vintage v ON v.id=o.vintage_id WHERE o.indicator_id=%s AND o.mode=%s
                AND o.reference_period < %s AND v.known_at < %s
                ORDER BY o.reference_period DESC, v.known_at DESC LIMIT 1""",
                (p["indicator_id"], p["mode"], curr_obs["reference_period"], curr_obs["known_at"])).fetchone()

        curr_val = Decimal(str(curr_obs["value"]))
        prev_val = Decimal(str(prev_obs["value"])) if prev_obs else None
        delta_pp = (curr_val - prev_val) if prev_val is not None else None
        threshold = Decimal(str(target.get("threshold_value", "0.25")))

        target_breach = False
        target_bounds = None
        if target_id == "guidance_target:inflation_target_cmn":
            target_bounds = ["1.50", "4.50"]
            if is_latest_period:
                target_breach = curr_val > Decimal("4.50") or curr_val < Decimal("1.50")
        elif target_id == "guidance_target:selic_neutral_band":
            target_bounds = ["8.50", "10.50"]
            if is_latest_period:
                target_breach = curr_val > Decimal("10.50") or curr_val < Decimal("8.50")

        delta_material = (delta_pp is not None) and (abs(delta_pp) >= threshold)
        is_target_material = delta_material or target_breach

        if delta_material and target_breach:
            rule = "composite_materiality_v1"
        elif delta_material:
            rule = "delta_absolute"
        elif target_breach:
            rule = "target_breach"
        else:
            rule = "immaterial"

        if is_target_material:
            target_alert_id = fingerprint(dict(
                indicator=p["indicator_id"],
                target=target_id,
                vintage=str(p["vintage_id"]),
                reference_period=str(curr_obs["reference_period"]),
                rule=rule,
            ))
            evidence = {
                "indicator_id": p["indicator_id"],
                "target_node_id": target_id,
                "reference_period": str(curr_obs["reference_period"]),
                "current_value": str(curr_val),
                "previous_value": str(prev_val) if prev_val is not None else None,
                "delta_pp": str(delta_pp) if delta_pp is not None else "0.00",
                "threshold_pp": str(threshold),
                "target_breach": target_breach,
                "target_range": target_bounds,
                "rule": rule,
                "mode": p["mode"],
                "event_id": str(event["id"]),
                "classification": "official_target" if target_id == "guidance_target:inflation_target_cmn" else "illustrative_neutral_band",
                "publication_allowed": False
            }
            conn.execute("""INSERT INTO alert(id, scenario_run_id, severity, owner_role, sla_hours, status, review_status, evidence)
                VALUES (%s, NULL, 'material', 'Independent Reviewer', 48, 'new', 'pending_human_review', %s)
                ON CONFLICT (id) DO UPDATE SET evidence=EXCLUDED.evidence""",
                (target_alert_id, Jsonb(evidence)))

            conn.execute("""INSERT INTO outbox (id, event_type, payload, status, processed_at)
                VALUES (%s, 'MaterialReviewRequired', %s, 'processed', clock_timestamp())""",
                (uuid.uuid4(), Jsonb({"alert_id": target_alert_id, "evidence": evidence, "mode": p["mode"]})))


def drain(dsn, limit=1000):
    processed, failed = 0, 0
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        for _ in range(limit):
            with conn.transaction():
                # Keep causal processing order across workers; ingestion can proceed independently.
                conn.execute("SELECT pg_advisory_xact_lock(912803)")
                event = conn.execute("SELECT * FROM outbox WHERE status='pending' ORDER BY created_at,id LIMIT 1 FOR UPDATE").fetchone()
                if event is None:
                    break
                try:
                    with conn.transaction(), trace.get_tracer(__name__).start_as_current_span("process_event"):
                        process_event(conn, event)
                        conn.execute("UPDATE outbox SET processed_at=clock_timestamp(),status='processed' WHERE id=%s", (event["id"],))
                    processed += 1
                except Exception as exc:
                    logging.exception("Outbox processing failed: %s", event["id"])
                    conn.execute("""UPDATE outbox SET attempts=attempts+1,last_error=%s,
                        status=CASE WHEN attempts+1>=3 THEN 'dead_letter' ELSE 'pending' END WHERE id=%s""",
                        (str(exc), event["id"]))
                    failed += 1
        try:
            from .freshness import refresh_source_schedules
            refresh_source_schedules(conn)
        except Exception:
            pass
    return dict(processed=processed, failed=failed)
