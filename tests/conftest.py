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
        conn.execute("TRUNCATE alert,scenario_run,outbox,observation,vintage,ingestion_run,raw_capture,dynamic_simulations CASCADE")
    return dsn
