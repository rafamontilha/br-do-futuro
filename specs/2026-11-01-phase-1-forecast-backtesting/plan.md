# Plan — Phase 1: Backtesting de Forecasts por Vintage e Horizonte

## Task groups

### 1. Data layer (PostgreSQL)

> **Status (2026-11-01):** implementado em `db/009_forecast_backtesting.sql`, coberto por
> `tests/test_forecast_backtesting_schema.py`; `./scripts/verify.sh` verde (153 testes Python).
> Refinamentos sobre o plano original: `mode` no hash/unique do snapshot, `min_sample` em
> `backtest_run`, `origin_kind` e `unit` em `backtest_metric`, checks de benchmark
> (`source_ref` nulo; sazonal só mensal) e `forecast_origin_at <= created_at`.

1.1. Criar `db/009_forecast_backtesting.sql` com as tabelas `forecast_snapshot`,
     `backtest_run` e `backtest_metric` (campos conforme `requirements.md`), `CHECK`s de
     domínio (`origin_kind`, `forecast_source`, `target`, `mode`, `frequency`) e
     `CHECK (lower_value IS NULL OR interval_level IS NOT NULL)`.
1.2. Aplicar o trigger `reject_mutation` às três tabelas (append-only).
1.3. Índices: `forecast_snapshot(indicator_id, target_period, forecast_origin_at)`,
     `backtest_metric(run_id, indicator_id, horizon)`; `UNIQUE(inputs_hash, code_version)`
     em `backtest_run`.
1.4. Nenhum seed com valores inventados: snapshots de fixture são gerados pelo worker
     (grupo 2) a partir das trajetórias existentes, marcados `reconstructed`/`fixture`.

### 2. Captura de snapshots (Python worker)

> **Status (2026-11-02):** implementação em `ingestion/bdf/forecast_snapshots.py`
> e integração transacional em `worker.py`. Grupo 2 validado por 15 testes de snapshots
> em PostgreSQL `bdf_test`; `./scripts/verify.sh` aprovado com 168 testes Python,
> testes/vet Go, build/typecheck web e `git diff --check`.
> Trajetórias mutáveis são conservadoramente `reconstructed`; horizontes seguem a
> frequência nativa do catálogo, mesmo nos pontos anuais. Intervalos sem nível nominal
> são omitidos com contador explícito, sem inventar confiança. Benchmarks recebem os
> snapshots para parear origem, alvo e horizonte (ajuste da assinatura de 2.3).
> Nenhum gate, validação econômica ou aprovação humana declarado concluído.

2.1. Criar `ingestion/bdf/forecast_snapshots.py` com `capture_trajectory_snapshots(conn, as_of)`
     que lê `indicator_trajectories` com `conn.cursor(row_factory=dict_row)` e grava
     `forecast_snapshot` com ID determinístico (`ON CONFLICT DO NOTHING`).
2.2. `capture_scenario_snapshots(conn, scenario_run_id)` extraindo trajetórias de
     `scenario_run.outputs`, com `forecast_origin_at = scenario_run.created_at` e
     `input_vintage_id` a partir de `inputs`.
2.3. `compute_benchmark_snapshots(conn, indicator_id, origin_at)` gerando random walk e
     sazonal ingênuo (mensais) usando apenas observações com `vintage.known_at <= origin_at`.
2.4. Função pura `compute_horizon(frequency, last_known_period, target_period)` com testes.
2.5. Integrar a captura de cenário ao fluxo `ScenarioRecalculated` em `worker.py`
     (idempotente; falha de captura gera erro explícito, sem fallback silencioso).

### 3. Motor de backtesting (Python worker)
3.1. Criar `ingestion/bdf/backtesting.py` com `match_realized(conn, snapshot, target)`:
     `first_release` = observação da menor `known_at` para o período;
     `latest` = maior `known_at <= as_of`.
3.2. Rejeitar pares onde `forecast_origin_at >= known_at` do realizado (garantia ex-ante);
     excluir `reconstructed` das métricas ex-ante (podem ser calculadas em grupo separado,
     rotuladas).
3.3. Funções puras `mae`, `rmse`, `bias`, `interval_coverage`, `relative_mae` sobre listas
     de pares; `insufficient_sample` quando `n_obs < MIN_SAMPLE` (constante = 8).
3.4. `run_backtest(conn, as_of, mode)` calculando `inputs_hash`, gravando `backtest_run` +
     `backtest_metric` em uma transação; reexecução com mesmo hash retorna o run existente.
3.5. Comando CLI (`python -m bdf.backtesting --as-of ... --mode fixture`) para execução
     manual/replay.

### 4. API (Go)
4.1. Criar `services/api/backtests.go` com `handleGetBacktests`: último `backtest_run`
     com `as_of <= query as_of`, filtros `indicator_id`, `horizon`, `target`,
     `forecast_source`, `mode`; resposta inclui `run_id`, `code_version`, `as_of`,
     `mode` e flag `experimental: true`.
4.2. Registrar a rota `GET /v1/backtests` no roteador de `main.go`.
4.3. Adicionar ao `handleGetObservabilityMetrics` (plano `models`): nº de snapshots
     ex-ante, último run e cobertura de indicadores com backtest.
4.4. Testes em `services/api/main_test.go`: filtros, `as_of` (run futuro não aparece),
     resposta vazia sem erro, 400 para `target` inválido.

### 5. Web (Next.js)
5.1. Criar `web/app/components/ForecastBacktestPanel.tsx`: tabela por indicador ×
     horizonte (MAE, RMSE, viés, cobertura, MAE relativo ao random walk), alternância
     `first_release`/`latest`, badge "Experimental" e badge "Fixture" quando `mode = fixture`.
5.2. Exibir "Amostra insuficiente" em vez de números quando `insufficient_sample = true`.
5.3. Integrar o painel ao plano "Modelos & Cenários" do `ObservabilityPlanesPanel.tsx`
     com texto de limitação metodológica.
5.4. Tipos TypeScript para a resposta de `/v1/backtests`.

### 6. Tests & verification
6.1. `tests/test_backtesting.py`: métricas puras com valores conhecidos; cálculo de
     horizonte; rejeição de pares não ex-ante; `first_release` vs `latest` com série revisada;
     benchmarks sem vazamento de informação futura; idempotência do run.
6.2. Testes de integração com conexão `dict_row` (paridade com o daemon) no `bdf_test`.
6.3. Atualizar `scripts/smoke.py` para `GET /v1/backtests`.
6.4. Executar `./scripts/verify.sh` e registrar evidências em `validation.md`.
