import os
from pathlib import Path
import psycopg
import pytest

@pytest.fixture
def db():
    dsn = os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL required for PostgreSQL integration")
    with psycopg.connect(dsn) as conn:
        assert conn.execute("SELECT current_database()").fetchone()[0] == "bdf_test", "Refuse to reset non-test database"
        conn.execute(Path("db/001_foundation.sql").read_text())
        conn.execute(Path("db/002_dynamic_and_institutional.sql").read_text())
        conn.execute(Path("db/003_source_schedules_and_replay.sql").read_text())
        conn.execute(Path("db/004_proposals_and_guidance.sql").read_text())
        conn.execute(Path("db/005_audit_logs_and_security.sql").read_text())
        conn.execute(Path("db/006_expand_p0_indicators.sql").read_text())
        conn.execute(Path("db/007_trajectory_comparisons.sql").read_text())
        conn.execute(Path("db/008_dependency_engine_and_reviews.sql").read_text())
        conn.execute("TRUNCATE alert,scenario_run,outbox,observation,vintage,ingestion_run,raw_capture,dynamic_simulations,outbox_replay_audit,public_proposals,guidance_commitments,fiscal_calibrations,system_api_keys,decision_audit_log,indicator_trajectories,recalculation_plan,dependency_graph_edges,dependency_graph_nodes CASCADE")
        conn.execute(Path("db/004_proposals_and_guidance.sql").read_text())
        conn.execute(Path("db/005_audit_logs_and_security.sql").read_text())
        conn.execute(Path("db/006_expand_p0_indicators.sql").read_text())
        conn.execute(Path("db/007_trajectory_comparisons.sql").read_text())
        conn.execute(Path("db/008_dependency_engine_and_reviews.sql").read_text())
    return dsn
