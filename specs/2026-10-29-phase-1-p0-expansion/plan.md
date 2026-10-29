# Plan — Phase 1: Expansão do Núcleo P0 (PIB, Câmbio PTAX, Desocupação PNAD Contínua)

## Summary

Expandir o conjunto de indicadores econômicos P0 com a introdução de três séries fundamentais para a análise macroeconômica brasileira:
1. PIB Trimestral (IBGE SIDRA 5932).
2. Taxa de Câmbio USD/BRL PTAX (BCB SGS 10813).
3. Taxa de Desocupação PNAD Contínua (IBGE SIDRA 4099).

A implementação abrange o ciclo de vida completo: registro no catálogo com metadados de domínio e periodicidade, conectores de ingestão com captura de raw payload SHA-256 e quarentena, persistência bitemporal idempotente em PostgreSQL, exposição em endpoints da API Go com suporte a filtros e paginação, e integração na interface de usuário Next.js com fallback transparente de fixtures para ambientes offline.

## Architecture / Design

```text
[ Fontes Oficiais: IBGE SIDRA API + BCB SGS ]
                    │
                    ▼
[ Python Ingestion Connectors (ingestion/bdf/sources/) ]
   - Fetching com headers de proveniência & retries
   - Hashing SHA-256 do payload bruto
   - Armazenamento em raw_payloads (bytea imutável)
   - Validação de contrato e quarentena automática
   - Normalização temporal (Trimestre -> YYYY-01-01, Mês móvel -> YYYY-MM-01)
                    │
                    ▼
[ PostgreSQL Storage (db/) ]
   - 006_expand_p0_indicators.sql (catálogo atualizado)
   - indicator_observations (append-only com conhecimento temporal)
                    │
                    ▼
[ Go API Service (services/api/) ]
   - /v1/indicators (retorna as 6 séries P0 consolidadas)
   - /v1/observations (filtros por indicador, data, período e bitemporalidade as_of)
   - Paginação e métricas dos 4 planos refletindo as novas séries
                    │
                    ▼
[ Next.js Web App (web/app/) ]
   - Cards e gráficos no Observatório Econômico Nacional
   - Seleção de granularidade e badges de fonte/frequência
```

## Work Breakdown

### Phase 1: Database Migration & Catalog Extension
- **File:** `db/006_expand_p0_indicators.sql`
- Inserir as novas séries `IBGE_PIB_TRIMESTRAL_VAR`, `BCB_PTAX_USD_BRL` e `IBGE_PNADC_DESOCUPACAO` na tabela `indicators`.
- Garantir integridade de domínios (`real_activity`, `external_trade_fx`, `labor_market`).

### Phase 2: Ingestion Connectors & Contracts (Python)
- **Files:**
  - `ingestion/bdf/sources/ibge.py` (ou expansão de conectores IBGE SIDRA para PIB e PNADC).
  - `ingestion/bdf/sources/bcb.py` (expansão para suportar a série PTAX 10813).
  - `ingestion/bdf/contracts.py` (modelos Pydantic para validação das novas respostas).
  - `ingestion/bdf/pipeline.py` (registro e execução das novas tarefas de ingestão).
  - `tests/fixtures/ibge_pib_sample.json`, `tests/fixtures/bcb_ptax_sample.json`, `tests/fixtures/ibge_pnadc_sample.json`.
  - `tests/test_p0_expansion_ingestion.py`.

### Phase 3: Go API Updates & Integration Tests
- **Files:**
  - `services/api/main.go` / `services/api/repository.go` (validação de filtros de frequência trimestral/diária e consultas).
  - `services/api/main_test.go` (testes cobrindo os novos indicadores nas rotas `/v1/indicators` e `/v1/observations`).

### Phase 4: Web UI Integration (Next.js)
- **Files:**
  - `web/app/components/ObservatorySection.tsx` (ou componente equivalente de observação de indicadores).
  - Atualização dos tipos e cartões de visualização para acomodar unidades heterogêneas (`% a.a.`, `R$ / US$`, `%`).

### Phase 5: Verification & End-to-End Smoke Test
- Execução de `pytest tests/`, `go test ./...`, `go vet ./...`, `npm run build`.
- Atualização do script `scripts/smoke.py` para validar a presença e consistência das 6 séries macroeconômicas.

## Risk and Mitigation

- **Risco:** Falhas de rede ou indisponibilidade pontual das APIs de terceiros (SIDRA / BCB) em testes ou ambiente local.
  - **Mitigação:** Arquitetura hermética com fixtures locais (`--fixture-mode` ou fallback automático em teste) preservando os dados brutos oficiais capturados.
- **Risco:** Ambiguidade na representação de trimestres (ex.: data de início vs. data de término do período).
  - **Mitigação:** Regra canônica explícita de ancoragem no 1º dia do trimestre (`YYYY-01-01`, `YYYY-04-01`, `YYYY-07-01`, `YYYY-10-01`), documentada em contrato e catálogo.
