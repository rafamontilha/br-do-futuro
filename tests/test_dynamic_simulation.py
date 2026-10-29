import json
from decimal import Decimal
import uuid
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
import pytest

from bdf.scenario import fiscal_path, validate_assumptions, fingerprint
from bdf.worker import drain


def test_validate_and_fiscal_path_dynamic():
    assumptions = dict(interest="0.10", growth="0.05", primary="0.01", adjustment="0.00", horizon_years=5)
    traj = fiscal_path(70.0, assumptions)
    assert len(traj) == 5
    assert traj[0]["horizon_years"] == 1
    assert Decimal(traj[0]["debt_pct_gdp"]) > 0

    # Test horizon between 1 and 20
    with pytest.raises(ValueError, match="Horizon years"):
        fiscal_path(70.0, dict(assumptions, horizon_years=0))
    with pytest.raises(ValueError, match="Horizon years"):
        fiscal_path(70.0, dict(assumptions, horizon_years=25))

    # Test growth rate constraint
    with pytest.raises(ValueError, match="Growth rate must be strictly greater than -100%"):
        fiscal_path(70.0, dict(assumptions, growth="-1.0"))
    with pytest.raises(ValueError, match="Growth rate must be strictly greater than -100%"):
        fiscal_path(70.0, dict(assumptions, growth="-1.5"))

    # Test non-finite value
    with pytest.raises(ValueError, match="Non-finite"):
        fiscal_path(70.0, dict(assumptions, interest="NaN"))

    # Test missing required assumption
    with pytest.raises(ValueError, match="Missing required"):
        validate_assumptions(dict(interest="0.10"))


def test_dynamic_simulation_outbox_worker(db):
    sim_id = str(uuid.uuid4())
    assumptions = dict(interest="0.11", growth="0.04", primary="0.005", adjustment="0.00", horizon_years=3)
    
    with psycopg.connect(db) as conn:
        conn.execute("""
            INSERT INTO dynamic_simulations(simulation_id, base_debt_pct, assumptions, status)
            VALUES (%s, %s, %s, 'pending')
        """, (sim_id, Decimal("78.5"), Jsonb(assumptions)))
        
        event_id = uuid.uuid4()
        conn.execute("""
            INSERT INTO outbox(id, event_type, payload)
            VALUES (%s, 'DynamicSimulationRequested', %s)
        """, (event_id, Jsonb(dict(
            simulation_id=sim_id,
            base_debt_pct="78.5",
            assumptions=assumptions
        ))))

    drain_res = drain(db)
    assert drain_res["processed"] == 1
    assert drain_res["failed"] == 0

    with psycopg.connect(db, row_factory=dict_row) as conn:
        sim = conn.execute("SELECT * FROM dynamic_simulations WHERE simulation_id=%s", (sim_id,)).fetchone()
        assert sim["status"] == "completed"
        assert sim["completed_at"] is not None
        assert len(sim["results"]) == 3
        assert sim["results"][0]["horizon_years"] == 1


def test_dynamic_simulation_invalid_assumptions_handled(db):
    sim_id = str(uuid.uuid4())
    bad_assumptions = dict(interest="0.10", growth="-1.0", primary="0.00", horizon_years=4)
    
    with psycopg.connect(db) as conn:
        conn.execute("""
            INSERT INTO dynamic_simulations(simulation_id, base_debt_pct, assumptions, status)
            VALUES (%s, %s, %s, 'pending')
        """, (sim_id, Decimal("75.0"), Jsonb(bad_assumptions)))
        
        event_id = uuid.uuid4()
        conn.execute("""
            INSERT INTO outbox(id, event_type, payload)
            VALUES (%s, 'DynamicSimulationRequested', %s)
        """, (event_id, Jsonb(dict(
            simulation_id=sim_id,
            base_debt_pct="75.0",
            assumptions=bad_assumptions
        ))))

    drain_res = drain(db)
    assert drain_res["processed"] == 1

    with psycopg.connect(db, row_factory=dict_row) as conn:
        sim = conn.execute("SELECT * FROM dynamic_simulations WHERE simulation_id=%s", (sim_id,)).fetchone()
        assert sim["status"] == "failed"
        assert "Growth rate must be strictly greater than -100%" in sim["error"]


def test_institutional_actors_catalog(db):
    with psycopg.connect(db, row_factory=dict_row) as conn:
        actors = conn.execute("SELECT * FROM institutional_actors ORDER BY actor_id").fetchall()
        assert len(actors) == 7
        actor_ids = {a["actor_id"] for a in actors}
        assert actor_ids == {"EXEC", "LEG", "JUD", "BCB", "TCU", "SUB", "SOC"}

        roles = conn.execute("""
            SELECT * FROM indicator_institutional_roles
            WHERE indicator_id='br.debt.gross_pct_gdp'
        """).fetchall()
        assert len(roles) >= 3
