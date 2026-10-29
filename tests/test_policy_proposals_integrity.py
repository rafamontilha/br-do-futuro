import re
from pathlib import Path
import psycopg
import pytest

VALID_COMPETENCES = {
    "executive_decree",
    "ordinary_law",
    "supplementary_law",
    "constitutional_amendment",
}

VALID_PROPOSAL_STATUSES = {
    "hypothesis_under_review",
    "calibrated",
    "ready_for_peer_review",
}

VALID_GUIDANCE_STATUSES = {
    "experimental_hypothesis",
    "proposed_target",
    "under_evaluation",
}


def test_migration_004_sql_file_exists_and_contains_expected_tables():
    sql_path = Path("db/004_proposals_and_guidance.sql")
    assert sql_path.exists(), "db/004_proposals_and_guidance.sql must exist"
    content = sql_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS public_proposals" in content
    assert "CREATE TABLE IF NOT EXISTS guidance_commitments" in content
    assert "CREATE TABLE IF NOT EXISTS fiscal_calibrations" in content

    # Check canonical proposal IDs
    assert "prop-fiscal-mandatory-spending" in content
    assert "prop-infra-investment-acceleration" in content
    assert "prop-tax-reform-neutrality" in content

    # Check guidance commitments
    assert "comm-debt-stabilization-2030" in content
    assert "comm-inflation-convergence-2030" in content
    assert "comm-investment-rate-2030" in content
    assert "br.ipca.12m" in content, "Annual inflation commitment must bind to annual indicator (br.ipca.12m)"

    # Verify no automatic validation or ratification
    assert "validated" not in content.lower() or "not_validated" in content.lower()
    assert "ratified" not in content.lower()


def test_public_proposals_contract_and_governance(db):
    with psycopg.connect(db) as conn:
        rows = conn.execute("""
            SELECT id, title, policy_axis, status, problem_statement, causal_mechanism,
                   cost_estimate_annual_brl, funding_source, institutional_competence,
                   responsible_actors, counterfactual_summary, empirical_evidence
            FROM public_proposals
            ORDER BY id
        """).fetchall()

        assert len(rows) >= 3, "Policy Lab must contain at least 3 canonical proposals"

        proposal_ids = {r[0] for r in rows}
        assert "prop-fiscal-mandatory-spending" in proposal_ids
        assert "prop-infra-investment-acceleration" in proposal_ids
        assert "prop-tax-reform-neutrality" in proposal_ids

        for r in rows:
            prop_id, title, axis, status, problem, causal, cost, funding, competence, actors, counter, evidence = r
            assert title, f"Proposal {prop_id} missing title"
            assert status in VALID_PROPOSAL_STATUSES, f"Invalid status {status} for {prop_id}"
            assert "ratified" not in status and "validated" not in status, "Proposals cannot be auto-ratified"
            assert causal and len(causal) > 30, f"Proposal {prop_id} requires explicit causal mechanism"
            assert funding and len(funding) > 10, f"Proposal {prop_id} requires funding source"
            assert competence in VALID_COMPETENCES, f"Invalid competence {competence} in {prop_id}"
            assert isinstance(actors, list) and len(actors) >= 1, f"Proposal {prop_id} requires responsible actors"
            assert counter and len(counter) > 20, f"Proposal {prop_id} requires counterfactual"
            assert evidence and len(evidence) > 20, f"Proposal {prop_id} requires empirical evidence references"


def test_guidance_commitments_separation_and_governance(db):
    with psycopg.connect(db) as conn:
        commitments = conn.execute("""
            SELECT id, proposal_id, indicator_id, name, horizon_year, status,
                   baseline_period, baseline_value, target_value, forecast_value,
                   actual_latest_value, unit, human_review_required
            FROM guidance_commitments
            ORDER BY horizon_year, id
        """).fetchall()

        assert len(commitments) >= 3, "Guidance must contain at least 3 commitments"

        inflation_comm = next(c for c in commitments if c[0] == "comm-inflation-convergence-2030")
        assert inflation_comm[2] == "br.ipca.12m", "Annual inflation commitment must bind to an annual inflation series (br.ipca.12m)"
        assert inflation_comm[2] != "br.ipca.monthly", "Cannot bind annual inflation target to monthly variation indicator"

        for c in commitments:
            comm_id, prop_id, indicator, name, horizon, status, b_period, b_val, t_val, f_val, a_val, unit, review_req = c
            assert status in VALID_GUIDANCE_STATUSES, f"Guidance commitment {comm_id} must have experimental/proposed status"
            assert review_req is True, "Human review must be strictly required for all Guidance commitments"
            assert b_period and b_val is not None, f"Commitment {comm_id} must have valid baseline"
            assert t_val is not None, f"Commitment {comm_id} must have target value"
            assert unit, f"Commitment {comm_id} must have valid unit"
            assert a_val is None, f"Commitment {comm_id} must have actual_latest_value NULL until backed by traceable observations"


def test_fiscal_calibrations_integrity(db):
    with psycopg.connect(db) as conn:
        calibrations = conn.execute("""
            SELECT id, scenario_id, proposal_id, elasticity_revenue_gdp,
                   real_interest_rate_spread, primary_balance_shift_pct_gdp, notes
            FROM fiscal_calibrations
        """).fetchall()

        assert len(calibrations) >= 4, "Must have at least 4 fiscal calibrations"
        for cal in calibrations:
            cal_id, scenario, prop_id, elast, spread, shift, notes = cal
            assert scenario in ("baseline", "optimistic", "pessimistic")
            assert float(elast) > 0, "Elasticity must be positive"
            assert notes and len(notes) > 10, "Calibrations require technical notes"
