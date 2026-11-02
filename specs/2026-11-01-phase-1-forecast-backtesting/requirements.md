# Requirements — Phase 1: Backtesting de Forecasts por Vintage e Horizonte

> Item 4 do roadmap da Fase 1, **parte (a)**. A parte (b) — alertas por calendário e
> materialidade — fica para uma fase seguinte (decisão de escopo em 2026-11-01).

## Scope

**In scope:**
- Registro **append-only** de snapshots ex-ante de forecasts (`forecast_snapshot`): cada
  previsão fica congelada com a origem (`forecast_origin_at`), a vintage dos dados de entrada
  conhecida naquela data, o período-alvo, o horizonte, a versão do modelo e a fonte do forecast.
- Captura de snapshots a partir dos forecasts que já existem no sistema:
  - `indicator_trajectories.forecast_value` / `forecast_lower` / `forecast_upper`;
  - `scenario_run.outputs` (trajetórias projetadas por execução de cenário).
- Benchmarks ingênuos calculados internamente, usando só informação disponível na origem:
  - **random walk** (último valor conhecido na vintage de origem);
  - **sazonal ingênuo** para séries mensais (mesmo mês do ano anterior), quando aplicável.
- Motor de backtesting no worker Python (`ingestion/bdf/backtesting.py`):
  - casa cada snapshot com o realizado **na primeira vintage publicada** e também na
    **vintage mais recente** (dois alvos de avaliação: `first_release` e `latest`);
  - calcula por indicador × horizonte × fonte do forecast: erro, MAE, RMSE, viés (ME),
    cobertura do intervalo (quando há `lower`/`upper`), número de observações e razão
    MAE(modelo)/MAE(benchmark) (Theil-U simplificado);
  - grava resultados em `backtest_run` / `backtest_metric` com hash das entradas e
    versão de código, de forma idempotente e reproduzível.
- Separação explícita **ex-ante vs. ex-post**: nenhum snapshot pode ter `forecast_origin_at`
  posterior ao `known_at` da observação usada como realizado; snapshots reconstruídos a
  posteriori são marcados `origin_kind = 'reconstructed'` e nunca agregados com `ex_ante`.
- Endpoint `GET /v1/backtests` (Go) com filtros por `indicator_id`, `horizon`, `target`
  (`first_release` | `latest`), `forecast_source` e `mode`, respeitando `as_of`.
- Painel no plano "Modelos" do `ObservabilityPlanesPanel`, rotulado como **experimental**,
  exibindo métricas por horizonte e comparação com benchmark.

**Out of scope:**
- Alertas por calendário de publicação, atraso de fonte e deduplicação/supressão (fase seguinte).
- Ingestão de forecasts externos (Focus/BCB) como nova fonte.
- Relatório público de desempenho do modelo operacional (item 6 do roadmap da Fase 1).
- Recalibração automática de modelos a partir dos erros medidos.
- Publicação automática de qualquer métrica ou recomendação derivada do backtest.
- Testes estatísticos formais de superioridade (Diebold-Mariano etc.) — registrado como
  questão aberta.

### Data / fields

**`forecast_snapshot`** (append-only, trigger `reject_mutation`)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | text | Yes | hash determinístico de (`indicator_id`, `target_period`, `forecast_origin_at`, `forecast_source`, `model_version`, `mode`); a mesma tupla tem `UNIQUE` |
| `indicator_id` | text | Yes | ID canônico (ex.: `br.ipca.12m`) |
| `target_period` | date | Yes | período previsto |
| `forecast_origin_at` | timestamptz | Yes | instante em que o forecast foi feito/conhecido; `CHECK (forecast_origin_at <= created_at)` |
| `input_vintage_id` | uuid | No | vintage dos dados disponíveis na origem (FK `vintage`) |
| `horizon` | integer | Yes | `>= 0`; distância em períodos da frequência nativa (`target_period` − último período conhecido na origem) |
| `frequency` | text | Yes | `daily`, `monthly`, `quarterly`, `annual` |
| `forecast_source` | text | Yes | `trajectory`, `scenario_run`, `benchmark_random_walk`, `benchmark_seasonal_naive` (este só com `frequency = 'monthly'`) |
| `source_ref` | text | No | ID de `indicator_trajectories` ou `scenario_run` de origem; obrigatoriamente nulo para benchmarks |
| `model_version` | text | Yes | versão do modelo / benchmark |
| `point_value` | numeric | Yes | previsão pontual |
| `lower_value` / `upper_value` | numeric | No | intervalo completo ou ausente; `lower <= point <= upper` |
| `interval_level` | numeric | No | nível nominal em (0, 1) (ex.: 0.80); obrigatório se houver intervalo |
| `unit` | text | Yes | mesma unidade da observação |
| `origin_kind` | text | Yes | `ex_ante` ou `reconstructed` |
| `mode` | text | Yes | `fixture` ou `source` |
| `created_at` | timestamptz | Yes | default `clock_timestamp()` |

**`backtest_run`** (append-only)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | uuid | Yes | |
| `inputs_hash` | text | Yes | hash dos snapshots + observações usados; `UNIQUE(inputs_hash, code_version)` garante idempotência |
| `code_version` | text | Yes | versão do motor |
| `as_of` | timestamptz | Yes | conhecimento temporal usado na execução |
| `min_sample` | integer | Yes | limiar de amostra usado no run (reprodutibilidade de `insufficient_sample`) |
| `mode` | text | Yes | `fixture` ou `source` |
| `created_at` | timestamptz | Yes | |

**`backtest_metric`** (append-only; PK `run_id, indicator_id, horizon, forecast_source, target, origin_kind`)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `run_id` | uuid | Yes | FK `backtest_run` |
| `indicator_id` | text | Yes | |
| `horizon` | integer | Yes | `>= 0` |
| `forecast_source` | text | Yes | |
| `target` | text | Yes | `first_release` ou `latest` |
| `origin_kind` | text | Yes | `ex_ante` ou `reconstructed` — nunca agregados juntos |
| `unit` | text | Yes | unidade das métricas |
| `n_obs` | integer | Yes | `> 0` (grupos vazios não são gravados) |
| `mae`, `rmse`, `bias` | numeric | Yes | na unidade do indicador; `mae`, `rmse >= 0` |
| `interval_coverage` | numeric | No | fração em [0, 1] observada dentro do intervalo |
| `relative_mae_vs_rw` | numeric | No | `>= 0`; MAE / MAE do random walk no mesmo conjunto de pares |
| `insufficient_sample` | boolean | Yes | `true` quando `n_obs` < `backtest_run.min_sample` |

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Origem dos forecasts | Snapshots internos (trajetórias + `scenario_run`) + benchmarks ingênuos | Escolha do usuário; evita nova fonte externa nesta fase. |
| Persistência ex-ante | Nova tabela append-only `forecast_snapshot`, não `indicator_trajectories` | `indicator_trajectories` é mutável (`updated_at`, `UNIQUE(indicator_id, period_date, mode)`); sem um snapshot congelado não existe backtest ex-ante legítimo. |
| Alvo do realizado | Avaliar contra `first_release` **e** `latest` | Preserva vintages/revisões; separa erro de previsão de erro de revisão da fonte. |
| Benchmark | Random walk sempre; sazonal ingênuo só para séries mensais | Comparação mínima exigida por `tech-stack.md` ("backtests comparados a benchmarks simples"). |
| Amostra mínima | `insufficient_sample = true` quando `n_obs < 8` (proposta, a validar) | Evita apresentar métricas com amostras minúsculas como evidência de desempenho. |
| Idempotência | `UNIQUE(inputs_hash, code_version)` em `backtest_run` | Reexecução com as mesmas entradas não duplica resultados. |
| Exposição | `GET /v1/backtests` + painel "Modelos" experimental; sem publicação automática | Escolha do usuário; respeita AGENTS.md (sem Guidance/recomendação automática). |
| Dependências | Só stdlib + bibliotecas já presentes (sem statsmodels novo) | Métricas são aritméticas simples; nenhuma dependência nova sem aprovação. |
| Conexões SQL | `conn.cursor(row_factory=...)` explícito; testes com `dict_row` | Regras do AGENTS.md / paridade com daemons. |

## Context

- **Tom:** técnico e descritivo (`mission.md`); o painel deve dizer explicitamente
  "experimental", indicar `fixture` quando aplicável e nunca sugerir que o modelo "acerta"
  sem amostra suficiente. Pergunta invariante 7 ("nosso processo de previsão está melhorando?")
  é o propósito da feature.
- **Stack constraints:** Python worker (`ingestion/bdf/`), Go API (`services/api/`),
  Next.js (`web/`), PostgreSQL com migrações numeradas (`db/009_forecast_backtesting.sql`).
  Testes de integração só em `bdf_test`. `./scripts/verify.sh` antes do PR.
- **Existing patterns to follow:** estrutura das specs `2026-10-29-phase-1-comparison-panels`
  e `2026-10-30-phase-1-dependency-engine`; trigger `reject_mutation` para tabelas de
  evidência; filtros com `as_of` como em `trajectories.go`; métricas de observabilidade em
  `observability.go`.
- **Resolved (2026-11-01, aceito pelo usuário):** tabela append-only `forecast_snapshot`
  (decisão "Persistência ex-ante") e tratamento dos forecasts fixture como
  `origin_kind = 'reconstructed'`, `mode = 'fixture'`, fora das métricas ex-ante; o backtest
  ex-ante real só acumula a partir da captura em produção. Isso é decisão de escopo da
  feature, não validação metodológica nem ratificação.
- **Open questions:**
  1. Limiar de amostra mínima (`n_obs < 8`) — validar com a revisão metodológica.
  2. Definição de horizonte para séries anuais com dados mensais parciais (ex.: IPCA 12m em
     dezembro) — precisa de regra escrita em `specs/methodology.md`?
  3. Diebold-Mariano / testes de significância ficam para o relatório de desempenho (item 6)?

## Regras operacionais do motor — grupo 3 (2026-11-02)

- Erro = forecast − realizado; métricas usam `Decimal`. Cobertura usa apenas os pares
  com intervalo completo e retorna nulo quando nenhum intervalo está disponível.
- `as_of` deve ter timezone e não pode estar no futuro em relação ao PostgreSQL.
  Só entram snapshots já registrados (`created_at <= as_of`) e originados até o corte;
  `latest` significa última vintage **capturada no sistema** até o corte, sem afirmar
  consulta atual à fonte oficial.
- Um alvo cuja primeira publicação já era conhecida na origem é excluído para ambos
  os alvos de avaliação. Uma revisão posterior não o requalifica como previsão ex-ante.
  Snapshots reconstruídos elegíveis são agregados separadamente dos ex-ante.
- Random walk é pareado por indicador, modo, origem, período-alvo, horizonte, unidade,
  tipo de origem e mesma observação realizada. O MAE relativo só é calculado com
  benchmark para **toda** a amostra do grupo; falta de pares ou MAE do benchmark zero
  produz nulo. Versões concorrentes ambíguas do random walk geram erro explícito.
- O hash inclui o corte temporal normalizado UTC, modo, `MIN_SAMPLE` e todos os
  snapshots/realizados selecionados. A versão do motor integra a chave de idempotência.
  Reexecução com o mesmo corte/inputs/código retorna o mesmo run; outro corte é uma
  avaliação distinta, ainda que as observações não tenham mudado.
- Todas as métricas e o run são gravados em uma transação. Unidades incompatíveis,
  erros numéricos e falhas SQL propagam erro e não deixam resultados parciais.
- Estas são regras técnicas do piloto experimental; não ratificam metodologia nem
  demonstram desempenho econômico. Limiar 8 continua sujeito à revisão humana.

## Contrato de leitura — grupo 4 (2026-11-02)

- `GET /v1/backtests` retorna `{meta, experimental: true, run, data}`. `meta.as_of`
  é o corte da consulta; `run.as_of` é o corte do motor, com `run_id`, código, hash,
  limiar, modo e criação. Sem run conhecido: `run: null`, `data: []`.
- O último run do modo é escolhido por `as_of DESC, created_at DESC, id DESC`, exigindo
  ambas as datas até o corte. Os filtros `indicator_id`, `horizon`, `target` e
  `forecast_source` restringem suas métricas, sem buscar em execuções antigas.
  Tipos de origem são expostos em cada métrica sem agregação adicional.
- Modo padrão `source`. Sem banco, inclusive `fixture`, retorna 503. Parâmetros
  inválidos retornam 400; horizonte aceita inteiros de 0 a 2147483647. Nulos de
  cobertura/MAE relativo e o indicador de amostra insuficiente são preservados.
- `models.backtesting` expõe contagem de snapshots ex-ante de forecasts (excluindo
  benchmarks), último run, contagem/lista de indicadores com métricas nesse run e
  contagem separada de indicadores ex-ante. Esse bloco respeita modo/corte; os campos
  legados dos outros planos de observabilidade continuam globais.
- Na observabilidade, banco não configurado/inacessível mantém o estado da plataforma
  e retorna `backtesting: null`, `backtesting_status: unavailable`. Banco acessível com
  erro na consulta de backtesting retorna 503 explicitamente. `available` é sucesso
  técnico de leitura, não validação econômica.
