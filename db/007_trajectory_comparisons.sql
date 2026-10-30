-- Brasil do Futuro - Fase 1: Painéis de Realizado vs. Baseline, Forecast, Target e Cenário de Continuidade
-- Migração 007: Tabela de trajetórias multivariadas e dados de referência

CREATE TABLE IF NOT EXISTS indicator_trajectories (
    id text PRIMARY KEY,
    indicator_id text NOT NULL,
    period_date date NOT NULL,
    period_label text NOT NULL,
    actual_value numeric(16,6),
    baseline_value numeric(16,6),
    forecast_value numeric(16,6),
    forecast_lower numeric(16,6),
    forecast_upper numeric(16,6),
    target_value numeric(16,6),
    continuity_value numeric(16,6),
    unit text NOT NULL,
    calibration_status text NOT NULL CHECK (calibration_status IN ('official', 'illustrative', 'calibrated', 'preliminary')),
    source_agency text NOT NULL,
    as_of_valid_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    mode text NOT NULL DEFAULT 'fixture' CHECK (mode IN ('fixture', 'source')),
    UNIQUE (indicator_id, period_date, mode)
);

CREATE INDEX IF NOT EXISTS indicator_trajectories_lookup
    ON indicator_trajectories(indicator_id, mode, period_date);
CREATE INDEX IF NOT EXISTS indicator_trajectories_as_of
    ON indicator_trajectories(indicator_id, as_of_valid_until);

-- Seed de referência para os 6 indicadores canônicos do P0 (2022 a 2030)
INSERT INTO indicator_trajectories (
    id, indicator_id, period_date, period_label,
    actual_value, baseline_value, forecast_value, forecast_lower, forecast_upper,
    target_value, continuity_value, unit, calibration_status, source_agency, mode, as_of_valid_until
)
VALUES
    -- 1. IPCA acumulado em 12 meses (br.ipca.12m)
    ('traj-ipca-2022', 'br.ipca.12m', '2022-12-01', '2022', 5.79, 5.00, 5.80, 5.20, 6.40, 3.50, 5.50, 'percent_year', 'official', 'IBGE', 'fixture', '2023-01-15 09:00:00-03'),
    ('traj-ipca-2023', 'br.ipca.12m', '2023-12-01', '2023', 4.62, 4.50, 4.70, 4.10, 5.30, 3.25, 4.80, 'percent_year', 'official', 'IBGE', 'fixture', '2024-01-15 09:00:00-03'),
    ('traj-ipca-2024', 'br.ipca.12m', '2024-12-01', '2024', 4.83, 4.00, 4.60, 4.00, 5.20, 3.00, 4.50, 'percent_year', 'official', 'IBGE', 'fixture', '2025-01-15 09:00:00-03'),
    ('traj-ipca-2025', 'br.ipca.12m', '2025-12-01', '2025', NULL, 3.50, 3.90, 3.20, 4.60, 3.00, 4.20, 'percent_year', 'illustrative', 'Focus/Model', 'fixture', NULL),
    ('traj-ipca-2026', 'br.ipca.12m', '2026-12-01', '2026', NULL, 3.50, 3.60, 3.00, 4.30, 3.00, 4.10, 'percent_year', 'illustrative', 'Focus/Model', 'fixture', NULL),
    ('traj-ipca-2027', 'br.ipca.12m', '2027-12-01', '2027', NULL, 3.00, 3.50, 2.80, 4.20, 3.00, 4.00, 'percent_year', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-ipca-2028', 'br.ipca.12m', '2028-12-01', '2028', NULL, 3.00, 3.30, 2.60, 4.00, 3.00, 3.90, 'percent_year', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-ipca-2029', 'br.ipca.12m', '2029-12-01', '2029', NULL, 3.00, 3.20, 2.50, 3.90, 3.00, 3.80, 'percent_year', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-ipca-2030', 'br.ipca.12m', '2030-12-01', '2030', NULL, 3.00, 3.00, 2.30, 3.70, 3.00, 3.80, 'percent_year', 'illustrative', 'Guidance/Model', 'fixture', NULL),

    -- 2. Selic meta anualizada (br.selic.target_annual)
    ('traj-selic-2022', 'br.selic.target_annual', '2022-12-01', '2022', 13.75, 9.50, 13.75, 13.00, 14.25, NULL, 13.00, 'percent_year', 'official', 'BCB', 'fixture', '2022-12-31 18:00:00-03'),
    ('traj-selic-2023', 'br.selic.target_annual', '2023-12-01', '2023', 11.75, 9.50, 11.75, 11.25, 12.25, NULL, 11.50, 'percent_year', 'official', 'BCB', 'fixture', '2023-12-31 18:00:00-03'),
    ('traj-selic-2024', 'br.selic.target_annual', '2024-12-01', '2024', 11.25, 9.50, 11.25, 10.75, 11.75, NULL, 11.00, 'percent_year', 'official', 'BCB', 'fixture', '2024-12-31 18:00:00-03'),
    ('traj-selic-2025', 'br.selic.target_annual', '2025-12-01', '2025', NULL, 9.00, 12.25, 11.50, 13.00, NULL, 12.00, 'percent_year', 'illustrative', 'Focus/Model', 'fixture', NULL),
    ('traj-selic-2026', 'br.selic.target_annual', '2026-12-01', '2026', NULL, 9.00, 11.50, 10.50, 12.50, NULL, 11.00, 'percent_year', 'illustrative', 'Focus/Model', 'fixture', NULL),
    ('traj-selic-2027', 'br.selic.target_annual', '2027-12-01', '2027', NULL, 8.50, 10.00, 9.00, 11.00, NULL, 10.50, 'percent_year', 'illustrative', 'Model', 'fixture', NULL),
    ('traj-selic-2028', 'br.selic.target_annual', '2028-12-01', '2028', NULL, 8.50, 9.50, 8.50, 10.50, NULL, 10.00, 'percent_year', 'illustrative', 'Model', 'fixture', NULL),
    ('traj-selic-2029', 'br.selic.target_annual', '2029-12-01', '2029', NULL, 8.00, 9.00, 8.00, 10.00, NULL, 9.50, 'percent_year', 'illustrative', 'Model', 'fixture', NULL),
    ('traj-selic-2030', 'br.selic.target_annual', '2030-12-01', '2030', NULL, 8.00, 8.50, 7.50, 9.50, NULL, 9.00, 'percent_year', 'illustrative', 'Model', 'fixture', NULL),

    -- 3. Dívida bruta do governo geral % PIB (br.debt.gross_pct_gdp)
    ('traj-debt-2022', 'br.debt.gross_pct_gdp', '2022-12-01', '2022', 71.7, 75.0, 72.0, 70.0, 74.0, 70.0, 73.0, 'percent_gdp', 'official', 'BCB/STN', 'fixture', '2023-01-30 09:00:00-03'),
    ('traj-debt-2023', 'br.debt.gross_pct_gdp', '2023-12-01', '2023', 74.4, 75.0, 75.0, 73.0, 77.0, 72.0, 76.0, 'percent_gdp', 'official', 'BCB/STN', 'fixture', '2024-01-30 09:00:00-03'),
    ('traj-debt-2024', 'br.debt.gross_pct_gdp', '2024-12-01', '2024', 78.6, 76.0, 78.0, 76.0, 80.0, 75.0, 80.0, 'percent_gdp', 'official', 'BCB/STN', 'fixture', '2025-01-30 09:00:00-03'),
    ('traj-debt-2025', 'br.debt.gross_pct_gdp', '2025-12-01', '2025', NULL, 77.0, 80.5, 78.5, 82.5, 76.5, 83.0, 'percent_gdp', 'illustrative', 'Model/STN', 'fixture', NULL),
    ('traj-debt-2026', 'br.debt.gross_pct_gdp', '2026-12-01', '2026', NULL, 78.0, 82.0, 79.5, 84.5, 77.0, 85.5, 'percent_gdp', 'illustrative', 'Model/STN', 'fixture', NULL),
    ('traj-debt-2027', 'br.debt.gross_pct_gdp', '2027-12-01', '2027', NULL, 78.0, 81.5, 78.0, 85.0, 75.0, 87.0, 'percent_gdp', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-debt-2028', 'br.debt.gross_pct_gdp', '2028-12-01', '2028', NULL, 77.0, 80.0, 76.0, 84.0, 73.0, 88.5, 'percent_gdp', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-debt-2029', 'br.debt.gross_pct_gdp', '2029-12-01', '2029', NULL, 76.0, 78.5, 74.0, 83.0, 71.0, 90.0, 'percent_gdp', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-debt-2030', 'br.debt.gross_pct_gdp', '2030-12-01', '2030', NULL, 75.0, 76.5, 72.0, 81.5, 68.0, 91.5, 'percent_gdp', 'illustrative', 'Guidance/Model', 'fixture', NULL),

    -- 4. PIB trimestral variação % interanual (br.gdp.quarterly_yoy)
    ('traj-gdp-2022', 'br.gdp.quarterly_yoy', '2022-12-01', '2022', 3.0, 2.0, 2.9, 2.3, 3.5, 3.0, 2.2, 'percent_yoy', 'official', 'IBGE', 'fixture', '2023-03-02 09:00:00-03'),
    ('traj-gdp-2023', 'br.gdp.quarterly_yoy', '2023-12-01', '2023', 2.9, 2.0, 2.8, 2.2, 3.4, 3.0, 2.0, 'percent_yoy', 'official', 'IBGE', 'fixture', '2024-03-01 09:00:00-03'),
    ('traj-gdp-2024', 'br.gdp.quarterly_yoy', '2024-12-01', '2024', 3.3, 2.2, 3.1, 2.5, 3.7, 3.0, 2.3, 'percent_yoy', 'official', 'IBGE', 'fixture', '2025-03-01 09:00:00-03'),
    ('traj-gdp-2025', 'br.gdp.quarterly_yoy', '2025-12-01', '2025', NULL, 2.2, 2.4, 1.8, 3.0, 2.8, 2.0, 'percent_yoy', 'illustrative', 'Focus/Model', 'fixture', NULL),
    ('traj-gdp-2026', 'br.gdp.quarterly_yoy', '2026-12-01', '2026', NULL, 2.3, 2.2, 1.5, 2.9, 3.0, 1.9, 'percent_yoy', 'illustrative', 'Focus/Model', 'fixture', NULL),
    ('traj-gdp-2027', 'br.gdp.quarterly_yoy', '2027-12-01', '2027', NULL, 2.5, 2.6, 1.8, 3.4, 3.5, 2.0, 'percent_yoy', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-gdp-2028', 'br.gdp.quarterly_yoy', '2028-12-01', '2028', NULL, 2.5, 2.8, 2.0, 3.6, 3.5, 2.1, 'percent_yoy', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-gdp-2029', 'br.gdp.quarterly_yoy', '2029-12-01', '2029', NULL, 2.5, 3.0, 2.1, 3.9, 3.8, 2.1, 'percent_yoy', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-gdp-2030', 'br.gdp.quarterly_yoy', '2030-12-01', '2030', NULL, 2.5, 3.2, 2.2, 4.2, 4.0, 2.2, 'percent_yoy', 'illustrative', 'Guidance/Model', 'fixture', NULL),

    -- 5. Câmbio USD/BRL PTAX (br.fx.usd_brl.ptax)
    ('traj-fx-2022', 'br.fx.usd_brl.ptax', '2022-12-01', '2022', 5.28, 5.10, 5.25, 4.90, 5.60, NULL, 5.30, 'brl_per_usd', 'official', 'BCB', 'fixture', '2022-12-31 18:00:00-03'),
    ('traj-fx-2023', 'br.fx.usd_brl.ptax', '2023-12-01', '2023', 4.86, 5.10, 4.90, 4.60, 5.20, NULL, 5.00, 'brl_per_usd', 'official', 'BCB', 'fixture', '2023-12-31 18:00:00-03'),
    ('traj-fx-2024', 'br.fx.usd_brl.ptax', '2024-12-01', '2024', 5.75, 5.15, 5.60, 5.20, 6.00, NULL, 5.80, 'brl_per_usd', 'official', 'BCB', 'fixture', '2024-12-31 18:00:00-03'),
    ('traj-fx-2025', 'br.fx.usd_brl.ptax', '2025-12-01', '2025', NULL, 5.20, 5.85, 5.50, 6.20, NULL, 6.00, 'brl_per_usd', 'illustrative', 'Focus/Model', 'fixture', NULL),
    ('traj-fx-2026', 'br.fx.usd_brl.ptax', '2026-12-01', '2026', NULL, 5.25, 5.90, 5.45, 6.35, NULL, 6.15, 'brl_per_usd', 'illustrative', 'Focus/Model', 'fixture', NULL),
    ('traj-fx-2027', 'br.fx.usd_brl.ptax', '2027-12-01', '2027', NULL, 5.30, 5.80, 5.30, 6.30, NULL, 6.25, 'brl_per_usd', 'illustrative', 'Model', 'fixture', NULL),
    ('traj-fx-2028', 'br.fx.usd_brl.ptax', '2028-12-01', '2028', NULL, 5.30, 5.75, 5.20, 6.30, NULL, 6.35, 'brl_per_usd', 'illustrative', 'Model', 'fixture', NULL),
    ('traj-fx-2029', 'br.fx.usd_brl.ptax', '2029-12-01', '2029', NULL, 5.35, 5.70, 5.10, 6.30, NULL, 6.45, 'brl_per_usd', 'illustrative', 'Model', 'fixture', NULL),
    ('traj-fx-2030', 'br.fx.usd_brl.ptax', '2030-12-01', '2030', NULL, 5.35, 5.65, 5.00, 6.30, NULL, 6.50, 'brl_per_usd', 'illustrative', 'Model', 'fixture', NULL),

    -- 6. Taxa de desocupação PNAD Contínua (br.labor.unemployment_rate)
    ('traj-unemp-2022', 'br.labor.unemployment_rate', '2022-12-01', '2022', 9.3, 10.5, 9.5, 8.8, 10.2, 8.5, 9.8, 'percent', 'official', 'IBGE', 'fixture', '2023-01-31 09:00:00-03'),
    ('traj-unemp-2023', 'br.labor.unemployment_rate', '2023-12-01', '2023', 7.8, 9.5, 8.0, 7.3, 8.7, 7.5, 8.2, 'percent', 'official', 'IBGE', 'fixture', '2024-01-31 09:00:00-03'),
    ('traj-unemp-2024', 'br.labor.unemployment_rate', '2024-12-01', '2024', 6.4, 9.0, 6.8, 6.2, 7.4, 7.0, 7.0, 'percent', 'official', 'IBGE', 'fixture', '2025-01-31 09:00:00-03'),
    ('traj-unemp-2025', 'br.labor.unemployment_rate', '2025-12-01', '2025', NULL, 8.5, 6.7, 6.0, 7.4, 6.5, 7.2, 'percent', 'illustrative', 'Model', 'fixture', NULL),
    ('traj-unemp-2026', 'br.labor.unemployment_rate', '2026-12-01', '2026', NULL, 8.5, 6.5, 5.8, 7.2, 6.0, 7.4, 'percent', 'illustrative', 'Model', 'fixture', NULL),
    ('traj-unemp-2027', 'br.labor.unemployment_rate', '2027-12-01', '2027', NULL, 8.0, 6.2, 5.4, 7.0, 5.5, 7.3, 'percent', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-unemp-2028', 'br.labor.unemployment_rate', '2028-12-01', '2028', NULL, 8.0, 6.0, 5.1, 6.9, 5.2, 7.2, 'percent', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-unemp-2029', 'br.labor.unemployment_rate', '2029-12-01', '2029', NULL, 7.5, 5.8, 4.9, 6.7, 5.0, 7.1, 'percent', 'illustrative', 'Guidance/Model', 'fixture', NULL),
    ('traj-unemp-2030', 'br.labor.unemployment_rate', '2030-12-01', '2030', NULL, 7.5, 5.5, 4.6, 6.4, 4.8, 7.0, 'percent', 'illustrative', 'Guidance/Model', 'fixture', NULL)
ON CONFLICT (indicator_id, period_date, mode) DO UPDATE SET
    period_label = EXCLUDED.period_label,
    actual_value = EXCLUDED.actual_value,
    baseline_value = EXCLUDED.baseline_value,
    forecast_value = EXCLUDED.forecast_value,
    forecast_lower = EXCLUDED.forecast_lower,
    forecast_upper = EXCLUDED.forecast_upper,
    target_value = EXCLUDED.target_value,
    continuity_value = EXCLUDED.continuity_value,
    unit = EXCLUDED.unit,
    calibration_status = EXCLUDED.calibration_status,
    source_agency = EXCLUDED.source_agency,
    as_of_valid_until = EXCLUDED.as_of_valid_until,
    updated_at = clock_timestamp();

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='bdf_reader') THEN
        GRANT SELECT ON indicator_trajectories TO bdf_reader;
    END IF;
END $$;
