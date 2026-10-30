import json
from decimal import Decimal
from pathlib import Path
import psycopg
import pytest

from bdf.catalog import INDICATORS, catalog
from bdf.pipeline import ingest, observations, validate


def fixture(name: str) -> bytes:
    return Path("fixtures", f"{name}.json").read_bytes()


def test_catalog_has_all_six_p0_indicators():
    cat = catalog()
    assert len(cat["domains"]) == 12
    indicator_ids = {ind["indicator_id"] for ind in cat["indicators"]}
    expected = {
        "br.ipca.monthly",
        "br.ipca.12m",
        "br.selic.daily",
        "br.debt.gross_pct_gdp",
        "br.gdp.quarterly_yoy",
        "br.fx.usd_brl.ptax",
        "br.labor.unemployment_rate",
    }
    assert expected.issubset(indicator_ids)


def test_source_schedules_contain_expanded_p0(db):
    with psycopg.connect(db) as conn:
        rows = conn.execute("""
            SELECT id, indicator_id, primary_source, frequency
            FROM source_schedules
            WHERE indicator_id IN ('br.gdp.quarterly_yoy', 'br.fx.usd_brl.ptax', 'br.labor.unemployment_rate')
            ORDER BY indicator_id
        """).fetchall()

    assert len(rows) == 3
    mapping = {r[1]: r for r in rows}
    assert mapping["br.gdp.quarterly_yoy"][2] == "IBGE_SIDRA"
    assert mapping["br.gdp.quarterly_yoy"][3] == "quarterly"

    assert mapping["br.fx.usd_brl.ptax"][2] == "BCB_SGS"
    assert mapping["br.fx.usd_brl.ptax"][3] == "daily"

    assert mapping["br.labor.unemployment_rate"][2] == "IBGE_SIDRA"
    assert mapping["br.labor.unemployment_rate"][3] == "quarterly"


def test_ingest_p0_fixtures_end_to_end_and_idempotent(db):
    # 1. Ingest GDP
    res_gdp = ingest(db, "br.gdp.quarterly_yoy", fixture("gdp"), "fixture:gdp.json")
    assert res_gdp["status"] == "accepted"
    assert res_gdp["changes"] == 2

    # Verify observations in db
    gdp_obs = observations(db, "br.gdp.quarterly_yoy")
    assert len(gdp_obs) == 2
    assert gdp_obs[0]["unit"] == "percent_yoy"
    assert Decimal(str(gdp_obs[0]["value"])) == Decimal("2.5")
    assert Decimal(str(gdp_obs[1]["value"])) == Decimal("2.9")

    # 2. Ingest FX PTAX
    res_fx = ingest(db, "br.fx.usd_brl.ptax", fixture("fx-ptax"), "fixture:fx-ptax.json")
    assert res_fx["status"] == "accepted"
    assert res_fx["changes"] == 2

    fx_obs = observations(db, "br.fx.usd_brl.ptax")
    assert len(fx_obs) == 2
    assert fx_obs[0]["unit"] == "brl_per_usd"
    assert Decimal(str(fx_obs[0]["value"])) == Decimal("6.1205")

    # 3. Ingest Unemployment
    res_unemp = ingest(db, "br.labor.unemployment_rate", fixture("unemployment"), "fixture:unemployment.json")
    assert res_unemp["status"] == "accepted"
    assert res_unemp["changes"] == 2

    unemp_obs = observations(db, "br.labor.unemployment_rate")
    assert len(unemp_obs) == 2
    assert unemp_obs[0]["unit"] == "percent"
    assert Decimal(str(unemp_obs[0]["value"])) == Decimal("7.5")

    # 4. Idempotency check: re-ingesting without changes
    res_gdp_repeat = ingest(db, "br.gdp.quarterly_yoy", fixture("gdp"), "fixture:gdp.json")
    assert res_gdp_repeat["status"] == "unchanged"
    assert res_gdp_repeat["changes"] == 0

    res_fx_repeat = ingest(db, "br.fx.usd_brl.ptax", fixture("fx-ptax"), "fixture:fx-ptax.json")
    assert res_fx_repeat["status"] == "unchanged"
    assert res_fx_repeat["changes"] == 0


def test_selic_target_annual_daily_validation():
    # BCB SGS 432 has daily frequency with dates of Copom decisions / business days
    payload = json.dumps([
        {"data": "19/09/2024", "valor": "10.75"},
        {"data": "07/11/2024", "valor": "11.25"},
    ]).encode("utf-8")

    parsed = validate(payload, INDICATORS["br.selic.target_annual"])
    assert len(parsed) == 2
    assert parsed[0][1] == Decimal("10.75")
    assert parsed[1][1] == Decimal("11.25")
