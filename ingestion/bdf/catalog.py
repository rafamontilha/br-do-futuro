"""Candidate series: approval and publication calendars are explicitly pending."""
DOMAINS = [
    "Crescimento e PIB", "Inflação e preços", "Juros e crédito", "Famílias e consumo",
    "Investimento e capital", "Câmbio e setor externo", "Comércio exterior",
    "Mercado financeiro", "Trabalho", "Demografia e sociedade", "Setores produtivos",
    "Contas públicas",
]
INDICATORS = {
    "br.ipca.monthly": dict(name="IPCA mensal", domain=2, series=433, unit="percent_month",
                            frequency="monthly", origin="IBGE via BCB/SGS", revisable=True),
    "br.ipca.12m": dict(name="IPCA acumulado em 12 meses", domain=2, series=13522, unit="percent_year",
                        frequency="monthly", origin="IBGE via BCB/SGS", revisable=True),
    "br.selic.daily": dict(name="Selic efetiva diária", domain=3, series=11, unit="percent_day",
                           frequency="daily", origin="BCB/SGS", revisable=True),
    "br.debt.gross_pct_gdp": dict(name="Dívida bruta do governo geral", domain=12, series=13762,
                                 unit="percent_gdp", frequency="monthly", origin="BCB/SGS", revisable=True),
}
for key, item in INDICATORS.items():
    item.update(indicator_id=key, geography="BR", adjustment="non-seasonally-adjusted",
                owner_role="Data Steward", methodology_version="sgs-contract-v1",
                license_status="pending_review", calendar_status="pending_validation",
                source_status="candidate", source_uri=f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{item['series']}/dados",
                quality_status="unavailable")


def catalog():
    return dict(methodology_version="constitution-1.3", domains=[
        dict(id=i, name=name, owner_role="Data Steward", owner_assignment="pending",
             coverage="pilot" if i in (2, 3, 12) else "planned")
        for i, name in enumerate(DOMAINS, 1)
    ], indicators=list(INDICATORS.values()))
