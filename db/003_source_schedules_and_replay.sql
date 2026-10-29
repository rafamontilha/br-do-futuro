-- Brasil do Futuro - Incremento 02: Fontes, Freshness e Replay Operacional
-- Migração 003

CREATE TABLE IF NOT EXISTS source_schedules (
    id text PRIMARY KEY,
    indicator_id text NOT NULL UNIQUE,
    primary_source text NOT NULL,
    fallback_source text,
    cron_expression text NOT NULL,
    frequency text NOT NULL CHECK (frequency IN ('daily', 'monthly', 'quarterly', 'annual')),
    expected_release_day_offset integer NOT NULL DEFAULT 10,
    expected_release_time time NOT NULL DEFAULT '09:00:00',
    tolerance_window_hours integer NOT NULL DEFAULT 4,
    last_checked_at timestamptz,
    last_successful_at timestamptz,
    next_expected_at timestamptz NOT NULL,
    is_stale boolean NOT NULL DEFAULT false,
    current_delay_hours numeric(8,2) NOT NULL DEFAULT 0.00,
    consecutive_failures integer NOT NULL DEFAULT 0,
    circuit_open boolean NOT NULL DEFAULT false,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS source_schedules_indicator ON source_schedules(indicator_id);
CREATE INDEX IF NOT EXISTS source_schedules_stale ON source_schedules(is_stale, next_expected_at);

CREATE TABLE IF NOT EXISTS outbox_replay_audit (
    id text PRIMARY KEY,
    triggered_by text NOT NULL,
    filter_event_type text,
    filter_indicator_id text,
    events_replayed_count integer NOT NULL DEFAULT 0,
    reason text NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    completed_at timestamptz
);

CREATE INDEX IF NOT EXISTS outbox_replay_audit_status ON outbox_replay_audit(status, created_at DESC);

-- Carga inicial de agendamentos oficiais para as 3 séries prioritárias
INSERT INTO source_schedules (
    id, indicator_id, primary_source, fallback_source, cron_expression, frequency,
    expected_release_day_offset, expected_release_time, tolerance_window_hours,
    next_expected_at, is_stale, current_delay_hours, consecutive_failures, circuit_open, metadata
)
VALUES
    (
        'sched-ipca',
        'br.ipca.monthly',
        'IBGE_SIDRA',
        'BCB_SGS',
        '0 9 10 * *',
        'monthly',
        10,
        '09:00:00',
        4,
        '2026-11-10 09:00:00-03',
        false,
        0.00,
        0,
        false,
        '{"sidra_table": 1737, "sidra_variable": 2265, "sgs_code": 433, "agency": "IBGE", "notes": "IPCA mensal primário via IBGE SIDRA com contingência BCB SGS"}'::jsonb
    ),
    (
        'sched-selic',
        'br.selic.daily',
        'BCB_SGS',
        NULL,
        '0 9 * * 1-5',
        'daily',
        1,
        '09:00:00',
        4,
        '2026-10-30 09:00:00-03',
        false,
        0.00,
        0,
        false,
        '{"sgs_code": 11, "agency": "BCB", "notes": "Taxa Selic apurada diariamente pelo Banco Central"}'::jsonb
    ),
    (
        'sched-debt',
        'br.debt.gross_pct_gdp',
        'BCB_SGS',
        NULL,
        '0 9 30 * *',
        'monthly',
        30,
        '09:30:00',
        6,
        '2026-10-31 09:30:00-03',
        false,
        0.00,
        0,
        false,
        '{"sgs_code": 13762, "agency": "BCB", "notes": "Dívida Bruta do Governo Geral (% PIB) apurada mensalmente"}'::jsonb
    )
ON CONFLICT (indicator_id) DO NOTHING;

-- Permissões para bdf_reader
GRANT SELECT, INSERT, UPDATE ON source_schedules TO bdf_reader;
GRANT SELECT, INSERT, UPDATE ON outbox_replay_audit TO bdf_reader;
