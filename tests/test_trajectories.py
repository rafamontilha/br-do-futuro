import json
from datetime import datetime
from pathlib import Path
import psycopg
import pytest

from bdf.catalog import catalog


def test_trajectories_fixture_integrity():
    path = Path("fixtures/trajectories.json")
    assert path.exists(), "fixtures/trajectories.json must exist"

    data = json.loads(path.read_text())
    assert isinstance(data, list)
    assert len(data) >= 30, "expected at least 30 trajectory points across 6 P0 indicators"

    indicators = {pt["indicator_id"] for pt in data}
    expected_indicators = {
        "br.ipca.12m",
        "br.selic.target_annual",
        "br.debt.gross_pct_gdp",
        "br.gdp.quarterly_yoy",
        "br.fx.usd_brl.ptax",
        "br.labor.unemployment_rate",
    }
    assert expected_indicators.issubset(indicators), f"missing expected indicators: {expected_indicators - indicators}"

    valid_statuses = {"official", "illustrative", "calibrated", "preliminary"}

    for pt in data:
        assert pt["id"].startswith("traj-")
        assert pt["period_date"]
        datetime.strptime(pt["period_date"], "%Y-%m-%d")
        assert pt["period_label"]
        assert pt["calibration_status"] in valid_statuses
        assert pt["source_agency"]

        # Verifica consistência das bandas de incerteza do forecast
        if pt.get("forecast_value") is not None and pt.get("forecast_lower") is not None and pt.get("forecast_upper") is not None:
            assert pt["forecast_lower"] <= pt["forecast_value"] <= pt["forecast_upper"], (
                f"forecast bounds violated for {pt['id']}: lower={pt['forecast_lower']}, "
                f"val={pt['forecast_value']}, upper={pt['forecast_upper']}"
            )

        # Verifica consistência bitemporal
        if pt.get("as_of_valid_until"):
            assert pt["calibration_status"] == "official"


def test_trajectories_units_strictly_match_catalog():
    """Garante que todo indicador em trajectories.json existe no catálogo oficial

    e que sua unidade seja rigorosamente idêntica à unidade catalogada,
    impedindo a mistura indevida de taxas diárias com anualizadas (ex.: Selic diária vs Copom).
    """
    cat = catalog()
    cat_indicators = {ind["indicator_id"]: ind for ind in cat["indicators"]}

    traj_path = Path("fixtures/trajectories.json")
    trajectories = json.loads(traj_path.read_text())

    for pt in trajectories:
        ind_id = pt["indicator_id"]
        assert ind_id in cat_indicators, f"indicator {ind_id} in trajectories.json is not defined in catalog.json"

        cat_unit = cat_indicators[ind_id]["unit"]
        traj_unit = pt["unit"]
        assert traj_unit == cat_unit, (
            f"Unit mismatch for indicator {ind_id}: trajectory has '{traj_unit}' but catalog defines '{cat_unit}'"
        )


def test_db_trajectories_schema_and_seed(db):
    with psycopg.connect(db) as conn:
        # Verifica se a tabela indicator_trajectories foi criada
        cols = conn.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'indicator_trajectories'
            ORDER BY ordinal_position
        """).fetchall()
        col_names = {c[0] for c in cols}
        expected_cols = {
            "id", "indicator_id", "period_date", "period_label",
            "actual_value", "baseline_value", "forecast_value",
            "forecast_lower", "forecast_upper", "target_value",
            "continuity_value", "unit", "calibration_status",
            "source_agency", "as_of_valid_until", "created_at", "updated_at"
        }
        assert expected_cols.issubset(col_names)

        # Verifica contagem de dados seed
        count = conn.execute("SELECT count(*) FROM indicator_trajectories").fetchone()[0]
        assert count >= 30, f"expected at least 30 seeded trajectory rows, found {count}"

        # Verifica que o corte temporal bitemporal funciona via SQL
        rows = conn.execute("""
            SELECT period_label,
                   CASE WHEN as_of_valid_until IS NOT NULL AND as_of_valid_until > '2023-01-01T00:00:00Z' THEN NULL ELSE actual_value END as masked_actual
            FROM indicator_trajectories
            WHERE indicator_id = 'br.ipca.12m'
            ORDER BY period_date ASC
        """).fetchall()
        for label, masked in rows:
            if label in ("2023", "2024"):
                assert masked is None, f"actual_value for {label} should be masked at 2023-01-01"


def test_bdf_reader_has_select_on_indicator_trajectories(db):
    """Garante que a role bdf_reader utilizada pela API em produção tem privilégios

    de leitura SELECT na tabela indicator_trajectories. Previne erro P1 de permission denied.
    """
    with psycopg.connect(db) as conn:
        role_exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'bdf_reader'").fetchone()
        if not role_exists:
            pytest.skip("bdf_reader role not configured in test environment")

        has_privilege = conn.execute(
            "SELECT has_table_privilege('bdf_reader', 'indicator_trajectories', 'SELECT')"
        ).fetchone()[0]
        assert has_privilege is True, "bdf_reader role must have SELECT privilege on indicator_trajectories table"
