import json
from datetime import date
from decimal import Decimal
import pytest

from bdf.sources.ibge import parse_ibge_ipca, IBGEContractError
from bdf.catalog import INDICATORS
from bdf.pipeline import validate


def test_parse_sidra_values_format():
    payload = json.dumps([
        {
            "NC": "Nível Territorial (Código)",
            "V": "Valor",
            "D2C": "Mês (Código)",
            "D3N": "Variável"
        },
        {
            "NC": "1",
            "V": "0.16",
            "D2C": "202501",
            "D3N": "IPCA - Variação mensal"
        },
        {
            "NC": "1",
            "V": "0.83",
            "D2C": "202502",
            "D3N": "IPCA - Variação mensal"
        }
    ]).encode("utf-8")

    result = parse_ibge_ipca(payload)
    assert len(result) == 2
    assert result[0] == (date(2025, 1, 1), Decimal("0.16"))
    assert result[1] == (date(2025, 2, 1), Decimal("0.83"))


def test_parse_agregados_format():
    payload = json.dumps([
        {
            "id": "2265",
            "variavel": "IPCA - Variação mensal",
            "unidade": "%",
            "resultados": [
                {
                    "classificacoes": [],
                    "series": [
                        {
                            "localidade": {"id": "1", "nivel": {"id": "N1", "nome": "Brasil"}, "nome": "Brasil"},
                            "serie": {
                                "202411": "0.36",
                                "202412": "0.52"
                            }
                        }
                    ]
                }
            ]
        }
    ]).encode("utf-8")

    result = parse_ibge_ipca(payload)
    assert len(result) == 2
    assert result[0] == (date(2024, 11, 1), Decimal("0.36"))
    assert result[1] == (date(2024, 12, 1), Decimal("0.52"))


def test_sidra_withheld_or_missing_raises_contract_error():
    payload = json.dumps([
        {"NC": "Header", "V": "Valor", "D2C": "Mês"},
        {"NC": "1", "V": "...", "D2C": "202501"}
    ]).encode("utf-8")

    with pytest.raises(IBGEContractError, match="Missing or withheld"):
        parse_ibge_ipca(payload)


def test_sidra_non_finite_raises_contract_error():
    payload = json.dumps([
        {"NC": "Header", "V": "Valor", "D2C": "Mês"},
        {"NC": "1", "V": "NaN", "D2C": "202501"}
    ]).encode("utf-8")

    with pytest.raises(IBGEContractError, match="Non-finite observation"):
        parse_ibge_ipca(payload)


def test_sidra_future_date_rejected():
    payload = json.dumps([
        {"NC": "Header", "V": "Valor", "D2C": "Mês"},
        {"NC": "1", "V": "0.40", "D2C": "209912"}
    ]).encode("utf-8")

    with pytest.raises(IBGEContractError, match="Future observation"):
        parse_ibge_ipca(payload)


def test_pipeline_validate_dispatches_to_ibge():
    payload = json.dumps([
        {"NC": "Nível", "V": "Valor", "D2C": "Mês"},
        {"NC": "1", "V": "0.25", "D2C": "202503"}
    ]).encode("utf-8")

    res = validate(payload, INDICATORS["br.ipca.monthly"])
    assert res == [(date(2025, 3, 1), Decimal("0.25"))]


def test_parse_quarterly_gdp_format():
    from bdf.sources.ibge import parse_ibge_sidra
    payload = json.dumps([
        {"NC": "Nível", "V": "Valor", "D2C": "Trimestre", "D3C": "Setores"},
        {"NC": "1", "V": "2.5", "D2C": "202404", "D3C": "90707"},
        {"NC": "1", "V": "2.9", "D2C": "202501", "D3C": "90707"}
    ]).encode("utf-8")

    result = parse_ibge_sidra(payload, frequency="quarterly")
    assert len(result) == 2
    assert result[0] == (date(2024, 10, 1), Decimal("2.5"))
    assert result[1] == (date(2025, 1, 1), Decimal("2.9"))


def test_parse_quarterly_invalid_quarter_raises_contract_error():
    from bdf.sources.ibge import parse_ibge_sidra
    payload = json.dumps([
        {"NC": "Header", "V": "Valor", "D2C": "Trimestre"},
        {"NC": "1", "V": "3.1", "D2C": "202505"}
    ]).encode("utf-8")

    with pytest.raises(IBGEContractError, match="Invalid quarter in period"):
        parse_ibge_sidra(payload, frequency="quarterly")


def test_pipeline_validate_gdp_quarterly():
    payload = json.dumps([
        {"NC": "Nível", "V": "Valor", "D2C": "Trimestre"},
        {"NC": "1", "V": "3.0", "D2C": "202402"}
    ]).encode("utf-8")

    result = validate(payload, INDICATORS["br.gdp.quarterly_yoy"])
    assert result == [(date(2024, 4, 1), Decimal("3.0"))]


def test_pipeline_validate_unemployment_quarterly():
    payload = json.dumps([
        {"NC": "Nível", "V": "Valor", "D2C": "Trimestre"},
        {"NC": "1", "V": "7.5", "D2C": "202403"}
    ]).encode("utf-8")

    result = validate(payload, INDICATORS["br.labor.unemployment_rate"])
    assert result == [(date(2024, 7, 1), Decimal("7.5"))]


def test_pipeline_validate_fx_ptax_daily():
    payload = json.dumps([
        {"data": "15/01/2025", "valor": "6.1205"},
        {"data": "16/01/2025", "valor": "6.1450"}
    ]).encode("utf-8")

    result = validate(payload, INDICATORS["br.fx.usd_brl.ptax"])
    assert len(result) == 2
    assert result[0] == (date(2025, 1, 15), Decimal("6.1205"))
    assert result[1] == (date(2025, 1, 16), Decimal("6.1450"))
