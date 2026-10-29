-- Brasil do Futuro - Fase 1: Expansão do Núcleo P0
-- Migração 006: Inclusão das séries PIB trimestral, Câmbio PTAX e Taxa de Desocupação PNADC

INSERT INTO source_schedules (
    id, indicator_id, primary_source, fallback_source, cron_expression, frequency,
    expected_release_day_offset, expected_release_time, tolerance_window_hours,
    next_expected_at, is_stale, current_delay_hours, consecutive_failures, circuit_open, metadata
)
VALUES
    (
        'sched-gdp-quarterly',
        'br.gdp.quarterly_yoy',
        'IBGE_SIDRA',
        NULL,
        '0 9 1 3,6,9,12 *',
        'quarterly',
        65,
        '09:00:00',
        6,
        '2026-12-01 09:00:00-03',
        false,
        0.00,
        0,
        false,
        '{"sidra_table": 5932, "sidra_variable": 6561, "sidra_classification": 11255, "sidra_category": 90707, "agency": "IBGE", "notes": "PIB a preços de mercado - taxa trimestral em relação ao mesmo período do ano anterior"}'::jsonb
    ),
    (
        'sched-fx-ptax',
        'br.fx.usd_brl.ptax',
        'BCB_SGS',
        NULL,
        '0 18 * * 1-5',
        'daily',
        1,
        '18:00:00',
        4,
        '2026-10-30 18:00:00-03',
        false,
        0.00,
        0,
        false,
        '{"sgs_code": 1, "agency": "BCB", "notes": "Taxa de câmbio - Livre - Dólar americano (venda) - diário PTAX"}'::jsonb
    ),
    (
        'sched-unemployment-rate',
        'br.labor.unemployment_rate',
        'IBGE_SIDRA',
        NULL,
        '0 9 15 2,5,8,11 *',
        'quarterly',
        45,
        '09:00:00',
        6,
        '2026-11-15 09:00:00-03',
        false,
        0.00,
        0,
        false,
        '{"sidra_table": 4099, "sidra_variable": 4099, "agency": "IBGE", "notes": "Taxa de desocupação da PNAD Contínua na semana de referência"}'::jsonb
    )
ON CONFLICT (indicator_id) DO UPDATE SET
    primary_source = EXCLUDED.primary_source,
    cron_expression = EXCLUDED.cron_expression,
    frequency = EXCLUDED.frequency,
    metadata = EXCLUDED.metadata,
    updated_at = clock_timestamp();
