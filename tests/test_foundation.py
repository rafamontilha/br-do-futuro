import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from bdf.catalog import INDICATORS, catalog
from bdf.pipeline import ingest, observations, validate
from bdf.scenario import fiscal_path
from bdf.worker import drain

DEBT = "br.debt.gross_pct_gdp"




def fixture(name):
    return Path("fixtures", name + ".json").read_bytes()


def test_contract_and_domain_catalog():
    assert len(catalog()["domains"]) == 12
    assert validate(fixture("debt-initial"), INDICATORS[DEBT])[0][1] == Decimal("70")

@pytest.mark.parametrize("value", ["NaN", "Infinity", "bad"])
def test_nonfinite_values(value):
    with pytest.raises((ValueError, ArithmeticError)):
        validate(json.dumps([dict(data="01/01/2025", valor=value)]), INDICATORS[DEBT])

@pytest.mark.parametrize("body", [b'[]', b'{}', b'[{"data":"02/01/2025","valor":"1"}]',
    b'[{"data":"01/01/2025","valor":"1"},{"data":"01/01/2025","valor":"2"}]',
    b'[{"data":"01/01/2999","valor":"1"}]', b'[{"data":"01/01/2025","valor":1}]'])
def test_bad_contract(body):
    with pytest.raises(ValueError):
        validate(body, INDICATORS[DEBT])


def test_fiscal_units_and_growth_constraint():
    assumptions=dict(interest="0.10", growth="0.10", primary="0.01", adjustment="0")
    assert Decimal(fiscal_path(70, assumptions)[0]["debt_pct_gdp"]) == 69
    with pytest.raises(ValueError):
        fiscal_path(70, dict(assumptions, growth="-1"))


def test_revision_as_of_outbox_and_replay(db):
    first=ingest(db, DEBT, fixture("debt-initial"), "fixture:initial")
    assert first["changes"] == 2
    assert drain(db)["processed"] == 2
    before=datetime.now(timezone.utc)
    assert ingest(db, DEBT, fixture("debt-initial"), "fixture:initial")["status"] == "unchanged"
    assert ingest(db, DEBT, fixture("debt-revised"), "fixture:revision")["changes"] == 2
    assert observations(db, DEBT, before)[-1]["value"] == 71
    assert observations(db, DEBT)[-1]["value"] == 72
    assert observations(db, DEBT, datetime(2020,1,1,tzinfo=timezone.utc)) == []
    assert drain(db)["processed"] == 2
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM observation").fetchone()[0] == 4
        assert conn.execute("SELECT count(*) FROM scenario_run").fetchone()[0] == 6
        assert conn.execute("SELECT count(*) FROM alert WHERE review_status='pending_human_review'").fetchone()[0] == 3
        hashes=conn.execute("SELECT id FROM scenario_run ORDER BY id").fetchall()
        conn.execute("UPDATE outbox SET status='pending',processed_at=NULL")
    drain(db)
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT id FROM scenario_run ORDER BY id").fetchall() == hashes
        assert conn.execute("SELECT count(*) FROM alert").fetchone()[0] == 3


def test_quarantine_has_no_observation_or_scenario(db):
    assert ingest(db, DEBT, b'[{"data":"01/01/2025","valor":"NaN"}]', "fixture:bad")["status"] == "quarantined"
    drain(db)
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM observation").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM scenario_run").fetchone()[0] == 0
        assert conn.execute("SELECT event_type FROM outbox").fetchone()[0] == "DataQualityFailed"
        assert conn.execute("SELECT count(*) FROM raw_capture").fetchone()[0] == 1


def test_concurrent_idempotency(db):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:ingest(db, DEBT, fixture("debt-initial"), "fixture:concurrent"),range(4)))
    assert sum(r["changes"] for r in results) == 2
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM outbox").fetchone()[0] == 2


def test_mode_isolation_and_append_only(db):
    ingest(db, DEBT, fixture("debt-initial"), "fixture:synthetic")
    assert observations(db, DEBT, mode="source") == []
    with psycopg.connect(db) as conn:
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute("UPDATE observation SET value=0")


def test_unrelated_series_do_not_recalculate(db):
    ingest(db, "br.ipca.monthly", fixture("ipca"), "fixture:ipca")
    drain(db)
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM scenario_run").fetchone()[0] == 0


def test_worker_failure_is_retried_then_dead_letter(db, monkeypatch):
    ingest(db, DEBT, fixture("debt-initial"), "fixture:failure")
    def fail(*args):
        raise RuntimeError("injected failure")
    monkeypatch.setattr("bdf.worker.process_event",fail)
    assert drain(db)["failed"] == 6
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM outbox WHERE status='dead_letter' AND attempts=3").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM scenario_run").fetchone()[0] == 0


def test_revision_of_old_period_keeps_current_scenario(db):
    ingest(db, DEBT, fixture("debt-initial"), "fixture:initial")
    drain(db)
    old_revision=b'[{"data":"01/01/2025","valor":"69.0"},{"data":"01/02/2025","valor":"71.0"}]'
    ingest(db, DEBT, old_revision, "fixture:old-revision")
    drain(db)
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM scenario_run").fetchone()[0] == 3
        assert conn.execute("SELECT count(*) FROM alert").fetchone()[0] == 0


def test_value_reversion_creates_new_vintage(db):
    ingest(db, DEBT, fixture("debt-initial"), "fixture:a")
    ingest(db, DEBT, fixture("debt-revised"), "fixture:b")
    assert ingest(db, DEBT, fixture("debt-initial"), "fixture:a-again")["changes"] == 2
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM vintage").fetchone()[0] == 3
        assert conn.execute("SELECT count(*) FROM raw_capture").fetchone()[0] == 2
