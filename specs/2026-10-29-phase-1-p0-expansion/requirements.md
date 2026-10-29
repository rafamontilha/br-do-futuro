# Requirements — Phase 1: Expansão do Núcleo P0 (PIB, Câmbio PTAX, Desocupação PNAD Contínua)

## Scope

**In scope:**
- Catálogo: Registrar 3 novas séries canônicas de alta relevância (P0) no catálogo de indicadores:
  1. `IBGE_PIB_TRIMESTRAL_VAR` (IBGE SIDRA Tabela 5932 - PIB a preços de mercado, variação % em relação ao mesmo período do ano anterior).
  2. `BCB_PTAX_USD_BRL` (BCB SGS série 1 / Olinda - Câmbio comercial USD/BRL venda, fechamento e série temporal).
  3. `IBGE_PNADC_DESOCUPACAO` (IBGE SIDRA Tabela 4099 - Taxa de desocupação da PNAD Contínua, trimestral móvel, %).
- Ingestão Python:
  - Módulos conectores com validação de contrato para IBGE SIDRA (API REST) e BCB SGS/Olinda.
  - Armazenamento de payload bruto (`raw_payloads`) com SHA-256 imutável.
  - Quarentena para respostas com payloads anômalos ou quebras de contrato.
  - Deduplicação idempotente e bitemporalidade (`period_date` + `knowledge_time` / `vintage_date`).
  - Fixtures estáticas oficiais para execução hermética e offline em testes e desenvolvimento.
- Banco de Dados (PostgreSQL):
  - Migração `db/006_expand_p0_indicators.sql` inserindo os metadados dos novos indicadores, periodicidades e unidades no catálogo.
- API Go:
  - Consulta aos novos indicadores via `/v1/indicators` e `/v1/observations`.
  - Suporte à ordenação, paginação e filtro temporal/bitemporal (`as_of`).
- Frontend Next.js:
  - Exibição dos novos indicadores no painel do Observatório Econômico Nacional (`web/app/`).
  - Cards informativos com unidade, periodicidade (trimestral, diária/mensal, móvel), proveniência oficial e indicador de dados reais vs. fixtures.

**Out of scope:**
- Séries desagregadas setoriais (ex: PIB Agropecuária, Indústria e Serviços isolados) — previsto para refinamento posterior na Fase 1.
- Motor de recálculo seletivo com grafo de dependências complexo (próximo incremento da Fase 1).
- Automatização de publicação de guidance ou relatórios públicos.

### Data / fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `indicator_id` | string (VARCHAR 64) | Yes | Identificador canônico único (ex: `IBGE_PIB_TRIMESTRAL_VAR`, `BCB_PTAX_USD_BRL`, `IBGE_PNADC_DESOCUPACAO`) |
| `domain_id` | string (VARCHAR 64) | Yes | Domínio econômico associado (`real_activity`, `external_trade_fx`, `labor_market`) |
| `period_date` | date (DATE) | Yes | Ancoragem temporal do período: 1º dia do trimestre para PIB (`YYYY-01-01`, `YYYY-04-01`, etc.); 1º dia do mês móvel para PNAD; data diária para Câmbio |
| `value` | numeric (NUMERIC 16,6) | Yes | Valor medido na unidade oficial |
| `unit` | string (VARCHAR 32) | Yes | Unidade de medida (`percent_yoy`, `brl_per_usd`, `percent`) |
| `vintage_date` | timestamptz | Yes | Momento de conhecimento / publicação oficial |
| `raw_payload_id` | bigint | Yes | Referência ao payload bruto no ledger de evidência |
| `sha256_hash` | string (CHAR 64) | Yes | Hash criptográfico do payload capturado na fonte |

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Ancoragem Temporal Trimestral | 1º dia do trimestre (ex: Q1 = `YYYY-01-01`, Q2 = `YYYY-04-01`) | Garante ordenação uniforme, consultas bitemporais consistentes no Postgres e interoperabilidade com séries mensais e anuais sem necessidade de novos tipos de dados no SQL |
| Conector IBGE SIDRA | Conector REST para a API SIDRA do IBGE com fallback de fixtures | Segue o padrão de conformidade e integridade dos conectores BCB existentes, preservando o JSON bruto e isolando erros de rede |
| Conector BCB PTAX | Conector para SGS 1 (ou Olinda) com extração de cotação de venda | Série canônica e amplamente referenciada no mercado para taxas de câmbio nominais de fechamento |
| Validação e Quarentena | Pydantic contracts com verificação de tipo, faixas razoáveis e consistência | Impede inserção de observações corrompidas ou alterações silenciosas de formato da fonte |
| Visualização no Frontend | Cards dinâmicos no Observatório com badge de periodicidade e proveniência | Oferece transparência imediata ao usuário mantendo coerência com o design system existente |

## Context

- **Tone:** Neutro, auditável, rigoroso e baseado em evidências conforme `specs/mission.md`. Não qualificar variações de PIB, câmbio ou desemprego como "positivas" ou "negativas" sem contexto metodológico.
- **Stack constraints:** Python 3.12+ (Pydantic, httpx/urllib3), Go 1.22+ (pgx, standard library), Next.js 14+ (App Router, Tailwind CSS, TypeScript strict), PostgreSQL 16+.
- **Existing patterns to follow:**
  - Migrações numeradas em `db/`.
  - Ingestão em `ingestion/bdf/`.
  - Serviços de consulta em `services/api/`.
  - Testes em `tests/` (Python) e `services/api/*_test.go` (Go).
  - Fixtures de teste em `ingestion/tests/fixtures/` ou `tests/fixtures/`.
