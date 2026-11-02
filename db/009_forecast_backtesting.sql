-- Brasil do Futuro - Fase 1: Backtesting de Forecasts por Vintage e Horizonte
-- Migração 009: snapshots ex-ante de forecasts e resultados de backtesting (append-only)
--
-- Decisões (specs/2026-11-01-phase-1-forecast-backtesting/requirements.md):
--   * indicator_trajectories é mutável; forecasts só são avaliáveis se congelados aqui.
--   * Forecasts derivados das fixtures atuais entram como origin_kind = 'reconstructed'
--     e nunca são agregados com snapshots 'ex_ante'.
--   * Nenhum seed: snapshots são produzidos pelo worker, nunca inventados na migração.

-- 1. Snapshots de forecasts congelados na origem
CREATE TABLE IF NOT EXISTS forecast_snapshot (
    id text PRIMARY KEY,
    indicator_id text NOT NULL,
    target_period date NOT NULL,
    forecast_origin_at timestamptz NOT NULL,
    input_vintage_id uuid REFERENCES vintage(id),
    horizon integer NOT NULL CHECK (horizon >= 0),
    frequency text NOT NULL CHECK (frequency IN ('daily', 'monthly', 'quarterly', 'annual')),
    forecast_source text NOT NULL CHECK (forecast_source IN (
        'trajectory', 'scenario_run', 'benchmark_random_walk', 'benchmark_seasonal_naive'
    )),
    source_ref text,
    model_version text NOT NULL,
    point_value numeric NOT NULL,
    lower_value numeric,
    upper_value numeric,
    interval_level numeric CHECK (interval_level IS NULL OR (interval_level > 0 AND interval_level < 1)),
    unit text NOT NULL,
    origin_kind text NOT NULL CHECK (origin_kind IN ('ex_ante', 'reconstructed')),
    mode text NOT NULL CHECK (mode IN ('fixture', 'source')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    -- intervalo é completo ou ausente, e exige nível nominal declarado
    CONSTRAINT forecast_snapshot_interval_pair CHECK ((lower_value IS NULL) = (upper_value IS NULL)),
    CONSTRAINT forecast_snapshot_interval_level CHECK (lower_value IS NULL OR interval_level IS NOT NULL),
    CONSTRAINT forecast_snapshot_interval_order CHECK (
        lower_value IS NULL OR (lower_value <= point_value AND point_value <= upper_value)
    ),
    -- a origem nunca pode estar no futuro em relação ao registro
    CONSTRAINT forecast_snapshot_origin_not_future CHECK (forecast_origin_at <= created_at),
    -- benchmarks são calculados internamente e não referenciam artefato de origem
    CONSTRAINT forecast_snapshot_benchmark_ref CHECK (
        forecast_source NOT IN ('benchmark_random_walk', 'benchmark_seasonal_naive') OR source_ref IS NULL
    ),
    -- sazonal ingênuo só se aplica a séries mensais
    CONSTRAINT forecast_snapshot_seasonal_monthly CHECK (
        forecast_source <> 'benchmark_seasonal_naive' OR frequency = 'monthly'
    ),
    UNIQUE (indicator_id, target_period, forecast_origin_at, forecast_source, model_version, mode)
);

CREATE INDEX IF NOT EXISTS forecast_snapshot_lookup
    ON forecast_snapshot(indicator_id, target_period, forecast_origin_at);
CREATE INDEX IF NOT EXISTS forecast_snapshot_source
    ON forecast_snapshot(forecast_source, origin_kind, mode);

-- 2. Execuções de backtesting (idempotentes por hash de entradas + versão de código)
CREATE TABLE IF NOT EXISTS backtest_run (
    id uuid PRIMARY KEY,
    inputs_hash text NOT NULL,
    code_version text NOT NULL,
    as_of timestamptz NOT NULL,
    min_sample integer NOT NULL CHECK (min_sample > 0),
    mode text NOT NULL CHECK (mode IN ('fixture', 'source')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (inputs_hash, code_version)
);

CREATE INDEX IF NOT EXISTS backtest_run_as_of ON backtest_run(mode, as_of DESC);

-- 3. Métricas por indicador × horizonte × fonte × alvo de realizado × tipo de origem
CREATE TABLE IF NOT EXISTS backtest_metric (
    run_id uuid NOT NULL REFERENCES backtest_run(id),
    indicator_id text NOT NULL,
    horizon integer NOT NULL CHECK (horizon >= 0),
    forecast_source text NOT NULL CHECK (forecast_source IN (
        'trajectory', 'scenario_run', 'benchmark_random_walk', 'benchmark_seasonal_naive'
    )),
    target text NOT NULL CHECK (target IN ('first_release', 'latest')),
    origin_kind text NOT NULL CHECK (origin_kind IN ('ex_ante', 'reconstructed')),
    unit text NOT NULL,
    n_obs integer NOT NULL CHECK (n_obs > 0),
    mae numeric NOT NULL CHECK (mae >= 0),
    rmse numeric NOT NULL CHECK (rmse >= 0),
    bias numeric NOT NULL,
    interval_coverage numeric CHECK (interval_coverage IS NULL OR (interval_coverage >= 0 AND interval_coverage <= 1)),
    relative_mae_vs_rw numeric CHECK (relative_mae_vs_rw IS NULL OR relative_mae_vs_rw >= 0),
    insufficient_sample boolean NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (run_id, indicator_id, horizon, forecast_source, target, origin_kind)
);

CREATE INDEX IF NOT EXISTS backtest_metric_lookup
    ON backtest_metric(run_id, indicator_id, horizon);

-- 4. Evidência append-only (reutiliza reject_mutation de 001_foundation.sql)
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['forecast_snapshot','backtest_run','backtest_metric'] LOOP
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'immutable_' || t) THEN
   EXECUTE format('CREATE TRIGGER immutable_%I BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION reject_mutation()',t,t);
  END IF;
 END LOOP;
END $$;

-- 5. Leitura pública somente via papel de leitura
GRANT SELECT ON forecast_snapshot, backtest_run, backtest_metric TO bdf_reader;
