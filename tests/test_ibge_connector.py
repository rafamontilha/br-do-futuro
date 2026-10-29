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
