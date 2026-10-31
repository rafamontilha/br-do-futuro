from decimal import Decimal
import psycopg
from psycopg.rows import dict_row
import pytest

from bdf.dependency_engine import load_graph, get_downstream_nodes, resolve_recalculation_plan
from bdf.materiality import evaluate_materiality
from bdf.pipeline import ingest
from bdf.worker import drain


def test_dependency_graph_loading_and_topological_resolution(db):
    with psycopg.connect(db) as conn:
        nodes, adj = load_graph(conn)
        assert "indicator:br.debt.gross_pct_gdp" in nodes
        assert "model:fiscal_path_v1" in nodes
        assert "scenario:continuity" in nodes
        assert "guidance_target:debt_stabilization" in nodes

        # Test topological downstream resolution from debt indicator
        downstream = get_downstream_nodes(adj, "indicator:br.debt.gross_pct_gdp")
        target_ids = [e["target_node_id"] for e in downstream]
        assert "model:fiscal_path_v1" in target_ids
        assert "scenario:continuity" in target_ids
        assert "guidance_target:debt_stabilization" in target_ids

        # model:fiscal_path_v1 must appear before scenario:continuity
        model_idx = target_ids.index("model:fiscal_path_v1")
        continuity_idx = target_ids.index("scenario:continuity")
        assert model_idx < continuity_idx


def test_load_graph_with_dict_row_factory(db):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        conn.execute("""
            INSERT INTO dependency_graph_nodes (id, node_type, canonical_name, domain_id, description)
            VALUES ('indicator:custom.test.indicator', 'indicator', 'Custom Test Indicator', 1, 'Custom test description')
            ON CONFLICT (id) DO NOTHING
        """)
        conn.execute("""
            INSERT INTO dependency_graph_edges (id, source_node_id, target_node_id, relationship_type, materiality_rule, threshold_value)
            VALUES ('edge:custom_to_model', 'indicator:custom.test.indicator', 'model:fiscal_path_v1', 'direct_input', 'delta_absolute', 0.10)
            ON CONFLICT (source_node_id, target_node_id) DO NOTHING
        """)
        nodes, adj = load_graph(conn)
        assert "indicator:custom.test.indicator" in nodes
        assert nodes["indicator:custom.test.indicator"]["canonical_name"] == "Custom Test Indicator"
        assert any(e["source_node_id"] == "indicator:custom.test.indicator" for e in adj.get("indicator:custom.test.indicator", []))


def test_resolve_recalculation_plan_persists_in_db(db):
    with psycopg.connect(db) as conn:
        event = {
            "id": "e8412dc0-1234-4567-89ab-cdef01234567",
            "event_type": "EconomicIndicatorUpdated",
            "payload": {
                "indicator_id": "br.debt.gross_pct_gdp",
                "mode": "fixture",
                "vintage_id": "v-test-01"
            }
        }
        plan = resolve_recalculation_plan(conn, event)
        assert plan["trigger_indicator_id"] == "br.debt.gross_pct_gdp"
        assert plan["status"] == "executed"
        assert len(plan["affected_nodes"]) > 0

        # Verify database record
        saved = conn.execute("SELECT * FROM recalculation_plan WHERE id=%s", (plan["id"],)).fetchone()
        assert saved is not None
        assert saved[2] == "br.debt.gross_pct_gdp"
        assert saved[5] == "executed"


def test_multi_level_materiality_evaluation():
    # 1. Delta immaterial and no breach
    curr = [{"debt_pct_gdp": "75.20"}]
    prev = [{"debt_pct_gdp": "75.00"}]
    is_mat, ev = evaluate_materiality(curr, prev, "continuity", threshold=Decimal("0.50"), target_cap=Decimal("80.00"))
    assert not is_mat
    assert ev["rule"] == "immaterial"
    assert ev["publication_allowed"] is True

    # 2. Delta absolute material (delta = 0.60 >= 0.50) without target breach
    curr = [{"debt_pct_gdp": "75.60"}]
    prev = [{"debt_pct_gdp": "75.00"}]
    is_mat, ev = evaluate_materiality(curr, prev, "continuity", threshold=Decimal("0.50"), target_cap=Decimal("80.00"))
    assert is_mat
    assert ev["rule"] == "delta_absolute"
    assert ev["target_breach"] is False
    assert ev["publication_allowed"] is False

    # 3. Target breach (debt = 81.00 > 80.00) with small delta
    curr = [{"debt_pct_gdp": "81.00"}]
    prev = [{"debt_pct_gdp": "80.80"}]
    is_mat, ev = evaluate_materiality(curr, prev, "continuity", threshold=Decimal("0.50"), target_cap=Decimal("80.00"))
    assert is_mat
    assert ev["rule"] == "target_breach"
    assert ev["target_breach"] is True

    # 4. Composite (both delta and target breach)
    curr = [{"debt_pct_gdp": "82.50"}]
    prev = [{"debt_pct_gdp": "80.00"}]
    is_mat, ev = evaluate_materiality(curr, prev, "continuity", threshold=Decimal("0.50"), target_cap=Decimal("80.00"))
    assert is_mat
    assert ev["rule"] == "composite_materiality_v1"
    assert ev["target_breach"] is True


def test_worker_triggers_selective_recalculation_and_human_review_alert(db):
    fixture_initial = b'[{"data":"01/01/2024","valor":"70.0"}]'
    ingest(db, "br.debt.gross_pct_gdp", fixture_initial, "fixture:initial-test")
    drain(db)

    # Ingest a material revision (+3.0 p.p. in base debt)
    fixture_revised = b'[{"data":"01/01/2024","valor":"73.0"}]'
    ingest(db, "br.debt.gross_pct_gdp", fixture_revised, "fixture:revised-test")
    drain(db)

    with psycopg.connect(db) as conn:
        # Check recalculation plans were created
        plans = conn.execute("SELECT count(*) FROM recalculation_plan WHERE trigger_indicator_id='br.debt.gross_pct_gdp'").fetchone()[0]
        assert plans >= 1

        # Check alerts created with pending_human_review
        alerts = conn.execute("SELECT id, severity, owner_role, sla_hours, review_status, evidence FROM alert WHERE review_status='pending_human_review'").fetchall()
        assert len(alerts) >= 1
        first_alert = alerts[0]
        assert first_alert[1] == "material"
        assert first_alert[2] == "Independent Reviewer"
        assert first_alert[3] == 48
        assert first_alert[4] == "pending_human_review"
        assert "delta_pp" in first_alert[5]


def test_initial_run_evaluates_target_breach_without_previous_run(db):
    fixture_high_debt = b'[{"data":"01/01/2024","valor":"82.0"}]'
    ingest(db, "br.debt.gross_pct_gdp", fixture_high_debt, "fixture:high-debt-initial")
    drain(db)

    with psycopg.connect(db) as conn:
        alerts = conn.execute("""
            SELECT id, severity, review_status, evidence
            FROM alert
            WHERE review_status='pending_human_review'
        """).fetchall()
        assert len(alerts) >= 1
        found_target_breach = any(a[3].get("target_breach") is True for a in alerts)
        assert found_target_breach is True


def test_ipca_cmn_guidance_target_materiality(db):
    # Ingest IPCA 12m at 5.20% (breaching CMN ceiling of 4.50%)
    fixture_ipca_breach = b'[{"data":"01/01/2024","valor":"5.20"}]'
    ingest(db, "br.ipca.12m", fixture_ipca_breach, "fixture:ipca-high")
    drain(db)

    with psycopg.connect(db) as conn:
        alerts = conn.execute("""
            SELECT id, scenario_run_id, severity, review_status, evidence
            FROM alert
            WHERE evidence->>'target_node_id' = 'guidance_target:inflation_target_cmn'
        """).fetchall()
        assert len(alerts) == 1
        al = alerts[0]
        assert al[1] is None  # scenario_run_id is nullable for guidance targets
        assert al[2] == "material"
        assert al[3] == "pending_human_review"
        assert al[4]["target_breach"] is True
        assert al[4]["current_value"] == "5.20"


def test_selic_and_gdp_ingestion_do_not_corrupt_fiscal_scenarios(db):
    # Ingest baseline debt
    fixture_debt = b'[{"data":"01/01/2024","valor":"75.0"}]'
    ingest(db, "br.debt.gross_pct_gdp", fixture_debt, "fixture:debt-base")
    drain(db)

    # Ingest Selic (14.50%) and GDP (-1.50%)
    fixture_selic = b'[{"data":"01/01/2024","valor":"14.50"}]'
    fixture_gdp = b'[{"data":"01/01/2024","valor":"-1.50"}]'
    ingest(db, "br.selic.target_annual", fixture_selic, "fixture:selic-test")
    ingest(db, "br.gdp.quarterly_yoy", fixture_gdp, "fixture:gdp-test")
    res = drain(db)
    assert res["failed"] == 0

    with psycopg.connect(db) as conn:
        runs = conn.execute("SELECT inputs->>'debt_pct_gdp' FROM scenario_run").fetchall()
        assert len(runs) > 0
        # All scenario runs must use debt_pct_gdp 75.0, never 14.50 or -1.50
        for r in runs:
            assert r[0] == "75.0"
