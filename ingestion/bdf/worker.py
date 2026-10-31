"""Database-backed local queue; transaction makes acknowledgement and output atomic."""
import logging
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from opentelemetry import trace

import uuid
from .scenario import DEPENDENCIES, SCENARIOS, MODEL_VERSION, fiscal_path, fingerprint
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
    affected_scenario_ids = [
        node["node_id"].split(":", 1)[1]
        for node in plan.get("affected_nodes", [])
        if node["node_id"].startswith("scenario:") and node["node_id"].split(":", 1)[1] in SCENARIOS
    ]
    if not affected_scenario_ids:
        affected_scenario_ids = DEPENDENCIES.get(p["indicator_id"], [])

    for scenario_id in affected_scenario_ids:
        # Only information already visible at this event's ingestion time may be used.
        observation = conn.execute("""SELECT o.*,v.known_at FROM observation o
            JOIN vintage v ON v.id=o.vintage_id WHERE indicator_id=%s AND mode=%s
            AND v.known_at <= (SELECT known_at FROM vintage WHERE id=%s)
            ORDER BY reference_period DESC,v.known_at DESC LIMIT 1""",
            (p["indicator_id"], p["mode"], p["vintage_id"])).fetchone()
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

        # 2. Evaluate multi-level materiality rules (delta and target breach) if there is a previous run to compare
        if previous:
            is_material, evidence = evaluate_materiality(
                current_outputs=outputs,
                previous_outputs=previous["outputs"],
                scenario_id=scenario_id,
                threshold=Decimal("0.50"),
                target_cap=Decimal("80.00")
            )
            evidence["event_id"] = str(event["id"])

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
