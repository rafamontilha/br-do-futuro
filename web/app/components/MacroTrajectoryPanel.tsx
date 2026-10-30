"use client";

import React, { useState, useMemo } from "react";

export interface TrajectoryPoint {
  id: string;
  indicator_id: string;
  period_date: string;
  period_label: string;
  actual_value: number | null;
  baseline_value: number | null;
  forecast_value: number | null;
  forecast_lower: number | null;
  forecast_upper: number | null;
  target_value: number | null;
  continuity_value: number | null;
  unit: string;
  calibration_status: string;
  source_agency: string;
  as_of_valid_until?: string | null;
}

interface MacroTrajectoryPanelProps {
  initialTrajectories?: TrajectoryPoint[] | null;
  mode?: "source" | "fixture";
}

const INDICATOR_CONFIG: Record<
  string,
  { name: string; shortName: string; unitLabel: string; targetNote?: string }
> = {
  "br.ipca.12m": {
    name: "Inflação IPCA (Acumulada em 12 meses)",
    shortName: "IPCA 12m",
    unitLabel: "% a.a.",
  },
  "br.selic.target_annual": {
    name: "Taxa Básica de Juros (Meta Selic Anualizada)",
    shortName: "Meta Selic",
    unitLabel: "% a.a.",
    targetNote: "Meta oficial fixada pelo Copom (% a.a.)",
  },
  "br.debt.gross_pct_gdp": {
    name: "Dívida Bruta do Governo Geral (DBGG)",
    shortName: "Dívida / PIB",
    unitLabel: "% do PIB",
  },
  "br.gdp.quarterly_yoy": {
    name: "PIB Trimestral a Preços de Mercado (Variação Interanual)",
    shortName: "PIB Trimestral",
    unitLabel: "% a.a. (YoY)",
  },
  "br.fx.usd_brl.ptax": {
    name: "Taxa de Câmbio Comercial (USD/BRL PTAX Venda)",
    shortName: "Câmbio PTAX",
    unitLabel: "R$ / US$",
    targetNote: "Regime de câmbio flutuante (sem meta oficial de cotação)",
  },
  "br.labor.unemployment_rate": {
    name: "Taxa de Desocupação (PNAD Contínua)",
    shortName: "Desemprego PNADC",
    unitLabel: "% da força de trabalho",
  },
};

const defaultTrajectories: TrajectoryPoint[] = [
  // 1. IPCA
  { id: "traj-ipca-2022", indicator_id: "br.ipca.12m", period_date: "2022-12-01", period_label: "2022", actual_value: 5.79, baseline_value: 5.0, forecast_value: 5.8, forecast_lower: 5.2, forecast_upper: 6.4, target_value: 3.5, continuity_value: 5.5, unit: "percent_year", calibration_status: "preliminary", source_agency: "IBGE (Fixture)" },
  { id: "traj-ipca-2023", indicator_id: "br.ipca.12m", period_date: "2023-12-01", period_label: "2023", actual_value: 4.62, baseline_value: 4.5, forecast_value: 4.7, forecast_lower: 4.1, forecast_upper: 5.3, target_value: 3.25, continuity_value: 4.8, unit: "percent_year", calibration_status: "preliminary", source_agency: "IBGE (Fixture)" },
  { id: "traj-ipca-2024", indicator_id: "br.ipca.12m", period_date: "2024-12-01", period_label: "2024", actual_value: 4.83, baseline_value: 4.0, forecast_value: 4.6, forecast_lower: 4.0, forecast_upper: 5.2, target_value: 3.0, continuity_value: 4.5, unit: "percent_year", calibration_status: "preliminary", source_agency: "IBGE (Fixture)" },
  { id: "traj-ipca-2025", indicator_id: "br.ipca.12m", period_date: "2025-12-01", period_label: "2025", actual_value: null, baseline_value: 3.5, forecast_value: 3.9, forecast_lower: 3.2, forecast_upper: 4.6, target_value: 3.0, continuity_value: 4.2, unit: "percent_year", calibration_status: "illustrative", source_agency: "Focus/Model (Fixture)" },
  { id: "traj-ipca-2026", indicator_id: "br.ipca.12m", period_date: "2026-12-01", period_label: "2026", actual_value: null, baseline_value: 3.5, forecast_value: 3.6, forecast_lower: 3.0, forecast_upper: 4.3, target_value: 3.0, continuity_value: 4.1, unit: "percent_year", calibration_status: "illustrative", source_agency: "Focus/Model (Fixture)" },
  { id: "traj-ipca-2027", indicator_id: "br.ipca.12m", period_date: "2027-12-01", period_label: "2027", actual_value: null, baseline_value: 3.0, forecast_value: 3.5, forecast_lower: 2.8, forecast_upper: 4.2, target_value: 3.0, continuity_value: 4.0, unit: "percent_year", calibration_status: "illustrative", source_agency: "Guidance/Model (Fixture)" },
  { id: "traj-ipca-2028", indicator_id: "br.ipca.12m", period_date: "2028-12-01", period_label: "2028", actual_value: null, baseline_value: 3.0, forecast_value: 3.3, forecast_lower: 2.6, forecast_upper: 4.0, target_value: 3.0, continuity_value: 3.9, unit: "percent_year", calibration_status: "illustrative", source_agency: "Guidance/Model (Fixture)" },
  { id: "traj-ipca-2029", indicator_id: "br.ipca.12m", period_date: "2029-12-01", period_label: "2029", actual_value: null, baseline_value: 3.0, forecast_value: 3.2, forecast_lower: 2.5, forecast_upper: 3.9, target_value: 3.0, continuity_value: 3.8, unit: "percent_year", calibration_status: "illustrative", source_agency: "Guidance/Model (Fixture)" },
  { id: "traj-ipca-2030", indicator_id: "br.ipca.12m", period_date: "2030-12-01", period_label: "2030", actual_value: null, baseline_value: 3.0, forecast_value: 3.0, forecast_lower: 2.3, forecast_upper: 3.7, target_value: 3.0, continuity_value: 3.8, unit: "percent_year", calibration_status: "illustrative", source_agency: "Guidance/Model (Fixture)" },

  // 2. Selic
  { id: "traj-selic-2022", indicator_id: "br.selic.target_annual", period_date: "2022-12-01", period_label: "2022", actual_value: 13.75, baseline_value: 9.5, forecast_value: 13.75, forecast_lower: 13.0, forecast_upper: 14.25, target_value: null, continuity_value: 13.0, unit: "percent_year", calibration_status: "preliminary", source_agency: "BCB (Fixture)" },
  { id: "traj-selic-2023", indicator_id: "br.selic.target_annual", period_date: "2023-12-01", period_label: "2023", actual_value: 11.75, baseline_value: 9.5, forecast_value: 11.75, forecast_lower: 11.25, forecast_upper: 12.25, target_value: null, continuity_value: 11.5, unit: "percent_year", calibration_status: "preliminary", source_agency: "BCB (Fixture)" },
  { id: "traj-selic-2024", indicator_id: "br.selic.target_annual", period_date: "2024-12-01", period_label: "2024", actual_value: 11.25, baseline_value: 9.5, forecast_value: 11.25, forecast_lower: 10.75, forecast_upper: 11.75, target_value: null, continuity_value: 11.0, unit: "percent_year", calibration_status: "preliminary", source_agency: "BCB (Fixture)" },
  { id: "traj-selic-2025", indicator_id: "br.selic.target_annual", period_date: "2025-12-01", period_label: "2025", actual_value: null, baseline_value: 9.0, forecast_value: 12.25, forecast_lower: 11.5, forecast_upper: 13.0, target_value: null, continuity_value: 12.0, unit: "percent_year", calibration_status: "illustrative", source_agency: "Focus/Model (Fixture)" },
  { id: "traj-selic-2026", indicator_id: "br.selic.target_annual", period_date: "2026-12-01", period_label: "2026", actual_value: null, baseline_value: 9.0, forecast_value: 11.5, forecast_lower: 10.5, forecast_upper: 12.5, target_value: null, continuity_value: 11.0, unit: "percent_year", calibration_status: "illustrative", source_agency: "Focus/Model (Fixture)" },
  { id: "traj-selic-2027", indicator_id: "br.selic.target_annual", period_date: "2027-12-01", period_label: "2027", actual_value: null, baseline_value: 8.5, forecast_value: 10.0, forecast_lower: 9.0, forecast_upper: 11.0, target_value: null, continuity_value: 10.5, unit: "percent_year", calibration_status: "illustrative", source_agency: "Model (Fixture)" },
  { id: "traj-selic-2028", indicator_id: "br.selic.target_annual", period_date: "2028-12-01", period_label: "2028", actual_value: null, baseline_value: 8.5, forecast_value: 9.5, forecast_lower: 8.5, forecast_upper: 10.5, target_value: null, continuity_value: 10.0, unit: "percent_year", calibration_status: "illustrative", source_agency: "Model (Fixture)" },
  { id: "traj-selic-2029", indicator_id: "br.selic.target_annual", period_date: "2029-12-01", period_label: "2029", actual_value: null, baseline_value: 8.0, forecast_value: 9.0, forecast_lower: 8.0, forecast_upper: 10.0, target_value: null, continuity_value: 9.5, unit: "percent_year", calibration_status: "illustrative", source_agency: "Model (Fixture)" },
  { id: "traj-selic-2030", indicator_id: "br.selic.target_annual", period_date: "2030-12-01", period_label: "2030", actual_value: null, baseline_value: 8.0, forecast_value: 8.5, forecast_lower: 7.5, forecast_upper: 9.5, target_value: null, continuity_value: 9.0, unit: "percent_year", calibration_status: "illustrative", source_agency: "Model (Fixture)" },
];

export function MacroTrajectoryPanel({ initialTrajectories, mode = "source" }: MacroTrajectoryPanelProps) {
  const [selectedIndicator, setSelectedIndicator] = useState<string>("br.ipca.12m");
  const [hoveredPointIndex, setHoveredPointIndex] = useState<number | null>(null);
  const [showTable, setShowTable] = useState<boolean>(true);

  const isFixtureMode = mode === "fixture";
  const hasSourceData = initialTrajectories && initialTrajectories.length > 0;

  // Em modo source sem dados, não inventar dados e exibir estado vazio explícito
  if (!isFixtureMode && !hasSourceData) {
    return (
      <section aria-labelledby="trajectories-heading" className="my-8 rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-neutral-400"></span>
          <h2 id="trajectories-heading" className="text-xl font-bold tracking-tight text-neutral-900">
            Trajetórias Macroeconômicas Multi-Perspectiva
          </h2>
        </div>
        <p className="mt-4 text-sm text-neutral-600">
          Trajetórias oficiais em modo fonte indisponíveis ou aguardando ingestão na base de dados (modo <code>source</code>).
        </p>
      </section>
    );
  }

  const trajectories = hasSourceData ? initialTrajectories : defaultTrajectories;

  const points = useMemo(() => {
    return trajectories.filter((t) => t.indicator_id === selectedIndicator);
  }, [trajectories, selectedIndicator]);

  const config = INDICATOR_CONFIG[selectedIndicator] || {
    name: selectedIndicator,
    shortName: selectedIndicator,
    unitLabel: points[0]?.unit || "",
  };

  // Escala para o gráfico vetorial SVG
  const chartMetrics = useMemo(() => {
    if (points.length === 0) return null;
    const allVals: number[] = [];
    points.forEach((p) => {
      if (p.actual_value !== null) allVals.push(p.actual_value);
      if (p.baseline_value !== null) allVals.push(p.baseline_value);
      if (p.forecast_value !== null) allVals.push(p.forecast_value);
      if (p.forecast_lower !== null) allVals.push(p.forecast_lower);
      if (p.forecast_upper !== null) allVals.push(p.forecast_upper);
      if (p.target_value !== null) allVals.push(p.target_value);
      if (p.continuity_value !== null) allVals.push(p.continuity_value);
    });

    if (allVals.length === 0) return null;

    const rawMin = Math.min(...allVals);
    const rawMax = Math.max(...allVals);
    const pad = (rawMax - rawMin) * 0.15 || 1;
    const minVal = Math.floor(rawMin - pad);
    const maxVal = Math.ceil(rawMax + pad);

    const width = 800;
    const height = 320;
    const padding = { top: 30, right: 40, bottom: 40, left: 60 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const getX = (idx: number) => padding.left + (idx / Math.max(1, points.length - 1)) * chartW;
    const getY = (val: number) => padding.top + chartH - ((val - minVal) / Math.max(1, maxVal - minVal)) * chartH;

    return { width, height, padding, chartW, chartH, minVal, maxVal, getX, getY };
  }, [points]);

  const fmtVal = (v: number | null | undefined) => {
    if (v === null || v === undefined) return "—";
    return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 2 }).format(v);
  };

  const fmtDelta = (actual: number | null, reference: number | null) => {
    if (actual === null || reference === null) return "—";
    const delta = actual - reference;
    const sign = delta > 0 ? "+" : "";
    return `${sign}${new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 2 }).format(delta)}`;
  };

  return (
    <section aria-labelledby="trajectories-heading" className="my-8 rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
      {/* Banner de Proveniência em Modo Fixture */}
      {isFixtureMode && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 flex flex-col md:flex-row md:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-bold uppercase tracking-wider text-[11px] text-amber-800 bg-amber-200/80 px-2 py-0.5 rounded">
              Demonstrador Hermético (Fixture)
            </span>
            <span>
              Todos os dados e séries históricas nesta visualização são sintéticos/fixtures para testes e desenvolvimento. Não representam publicações oficiais.
            </span>
          </div>
          <span className="text-[10px] text-amber-700 font-mono">mode=fixture</span>
        </div>
      )}

      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b border-neutral-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className={`inline-block h-2.5 w-2.5 rounded-full ${isFixtureMode ? "bg-amber-500" : "bg-blue-600"}`}></span>
            <h2 id="trajectories-heading" className="text-xl font-bold tracking-tight text-neutral-900">
              Trajetórias Macroeconômicas Multi-Perspectiva
            </h2>
          </div>
          <p className="text-sm text-neutral-600 mt-1">
            Confronto temporal entre Realizado, Metas Institucionais, Baseline Histórico, Forecasts e Cenário Inercial.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium text-neutral-600 bg-neutral-100 px-3 py-1.5 rounded-lg">
          <span className="font-semibold text-neutral-800">Corte Metodológico:</span> Constituição V1.3 · P0
        </div>
      </div>

      {/* Seletor de Indicadores P0 */}
      <div className="mt-5 flex flex-wrap gap-2">
        {Object.entries(INDICATOR_CONFIG).map(([id, cfg]) => {
          const isSelected = selectedIndicator === id;
          return (
            <button
              key={id}
              onClick={() => {
                setSelectedIndicator(id);
                setHoveredPointIndex(null);
              }}
              className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition-all ${
                isSelected
                  ? "bg-blue-600 text-white shadow-sm ring-2 ring-blue-600 ring-offset-1"
                  : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
              }`}
            >
              {cfg.shortName}
            </button>
          );
        })}
      </div>

      {/* Cabeçalho do Indicador Ativo */}
      <div className="mt-5 rounded-lg bg-neutral-50 p-4 border border-neutral-200 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-neutral-900">{config.name}</h3>
          <p className="text-xs text-neutral-600">
            Unidade: <span className="font-medium text-neutral-800">{config.unitLabel}</span>
            {config.targetNote && (
              <span className="ml-2 text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                Nota: {config.targetNote}
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-neutral-900"></span>
            <span className="font-medium text-neutral-800">
              {isFixtureMode ? "Realizado (Sintético / Fixture)" : "Realizado Oficial"}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded bg-emerald-600"></span>
            <span className="font-medium text-neutral-800">Target (Meta Oficial)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded bg-blue-500"></span>
            <span className="font-medium text-neutral-800">Forecast (Projeção)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded bg-neutral-400"></span>
            <span className="font-medium text-neutral-800">Baseline</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded bg-amber-500"></span>
            <span className="font-medium text-neutral-800">Continuidade (Inercial)</span>
          </div>
        </div>
      </div>

      {/* Gráfico Vetorial SVG */}
      {chartMetrics && (
        <div className="mt-4 relative rounded-lg border border-neutral-200 bg-white p-2 overflow-x-auto">
          <svg
            viewBox={`0 0 ${chartMetrics.width} ${chartMetrics.height}`}
            className="w-full h-auto max-h-[360px]"
            role="img"
            aria-label={`Gráfico de trajetórias para ${config.name}`}
          >
            {/* Linhas de Grade Horizontais */}
            {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
              const val = chartMetrics.minVal + pct * (chartMetrics.maxVal - chartMetrics.minVal);
              const y = chartMetrics.getY(val);
              return (
                <g key={pct}>
                  <line
                    x1={chartMetrics.padding.left}
                    y1={y}
                    x2={chartMetrics.width - chartMetrics.padding.right}
                    y2={y}
                    stroke="#e5e7eb"
                    strokeDasharray="4 4"
                  />
                  <text
                    x={chartMetrics.padding.left - 8}
                    y={y + 4}
                    textAnchor="end"
                    fontSize="10"
                    fill="#6b7280"
                    fontWeight="500"
                  >
                    {fmtVal(val)}
                  </text>
                </g>
              );
            })}

            {/* Linhas de Grade Verticais e Rótulos dos Anos */}
            {points.map((p, idx) => {
              const x = chartMetrics.getX(idx);
              const isHovered = hoveredPointIndex === idx;
              return (
                <g key={p.id}>
                  <line
                    x1={x}
                    y1={chartMetrics.padding.top}
                    x2={x}
                    y2={chartMetrics.height - chartMetrics.padding.bottom}
                    stroke={isHovered ? "#93c5fd" : "#f3f4f6"}
                    strokeWidth={isHovered ? 2 : 1}
                  />
                  <text
                    x={x}
                    y={chartMetrics.height - chartMetrics.padding.bottom + 18}
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight={isHovered ? "bold" : "500"}
                    fill={isHovered ? "#1d4ed8" : "#4b5563"}
                  >
                    {p.period_label}
                  </text>
                </g>
              );
            })}

            {/* Área Sombreada da Banda de Incerteza do Forecast */}
            {(() => {
              const forecastPoints = points
                .map((p, idx) => ({ p, x: chartMetrics.getX(idx) }))
                .filter(({ p }) => p.forecast_lower !== null && p.forecast_upper !== null);

              if (forecastPoints.length > 1) {
                const upperPath = forecastPoints
                  .map(({ p, x }, i) => `${i === 0 ? "M" : "L"} ${x} ${chartMetrics.getY(p.forecast_upper!)}`)
                  .join(" ");
                const lowerPath = forecastPoints
                  .slice()
                  .reverse()
                  .map(({ p, x }) => `L ${x} ${chartMetrics.getY(p.forecast_lower!)}`)
                  .join(" ");

                return (
                  <path
                    d={`${upperPath} ${lowerPath} Z`}
                    fill="#bfdbfe"
                    fillOpacity="0.45"
                    className="transition-all"
                  />
                );
              }
              return null;
            })()}

            {/* Curva Baseline (Pontilhada cinza) */}
            {(() => {
              const pts = points
                .map((p, idx) => ({ p, x: chartMetrics.getX(idx) }))
                .filter(({ p }) => p.baseline_value !== null);
              if (pts.length > 1) {
                const d = pts.map(({ p, x }, i) => `${i === 0 ? "M" : "L"} ${x} ${chartMetrics.getY(p.baseline_value!)}`).join(" ");
                return <path d={d} fill="none" stroke="#9ca3af" strokeWidth="2" strokeDasharray="3 3" />;
              }
              return null;
            })()}

            {/* Curva Cenário de Continuidade (Tracejada âmbar) */}
            {(() => {
              const pts = points
                .map((p, idx) => ({ p, x: chartMetrics.getX(idx) }))
                .filter(({ p }) => p.continuity_value !== null);
              if (pts.length > 1) {
                const d = pts.map(({ p, x }, i) => `${i === 0 ? "M" : "L"} ${x} ${chartMetrics.getY(p.continuity_value!)}`).join(" ");
                return <path d={d} fill="none" stroke="#f59e0b" strokeWidth="2" strokeDasharray="6 3" />;
              }
              return null;
            })()}

            {/* Curva Target / Metas (Tracejada verde) */}
            {(() => {
              const pts = points
                .map((p, idx) => ({ p, x: chartMetrics.getX(idx) }))
                .filter(({ p }) => p.target_value !== null);
              if (pts.length > 1) {
                const d = pts.map(({ p, x }, i) => `${i === 0 ? "M" : "L"} ${x} ${chartMetrics.getY(p.target_value!)}`).join(" ");
                return (
                  <g>
                    <path d={d} fill="none" stroke="#059669" strokeWidth="2.5" strokeDasharray="5 4" />
                    {pts.map(({ p, x }) => (
                      <rect
                        key={`tgt-${p.id}`}
                        x={x - 3.5}
                        y={chartMetrics.getY(p.target_value!) - 3.5}
                        width="7"
                        height="7"
                        fill="#059669"
                        rx="1"
                      />
                    ))}
                  </g>
                );
              }
              return null;
            })()}

            {/* Curva Forecast (Linha azul com círculos) */}
            {(() => {
              const pts = points
                .map((p, idx) => ({ p, x: chartMetrics.getX(idx) }))
                .filter(({ p }) => p.forecast_value !== null);
              if (pts.length > 1) {
                const d = pts.map(({ p, x }, i) => `${i === 0 ? "M" : "L"} ${x} ${chartMetrics.getY(p.forecast_value!)}`).join(" ");
                return (
                  <g>
                    <path d={d} fill="none" stroke="#2563eb" strokeWidth="2.5" />
                    {pts.map(({ p, x }) => (
                      <circle
                        key={`fc-${p.id}`}
                        cx={x}
                        cy={chartMetrics.getY(p.forecast_value!)}
                        r="3.5"
                        fill="#2563eb"
                        stroke="#ffffff"
                        strokeWidth="1.5"
                      />
                    ))}
                  </g>
                );
              }
              return null;
            })()}

            {/* Curva Realizado (Linha preta sólida com marcadores destacados) */}
            {(() => {
              const pts = points
                .map((p, idx) => ({ p, x: chartMetrics.getX(idx) }))
                .filter(({ p }) => p.actual_value !== null);
              if (pts.length > 0) {
                const d = pts.map(({ p, x }, i) => `${i === 0 ? "M" : "L"} ${x} ${chartMetrics.getY(p.actual_value!)}`).join(" ");
                return (
                  <g>
                    <path d={d} fill="none" stroke="#111827" strokeWidth="3" />
                    {pts.map(({ p, x }) => (
                      <circle
                        key={`act-${p.id}`}
                        cx={x}
                        cy={chartMetrics.getY(p.actual_value!)}
                        r="5"
                        fill="#111827"
                        stroke="#ffffff"
                        strokeWidth="2"
                      />
                    ))}
                  </g>
                );
              }
              return null;
            })()}

            {/* Zonas Interativas Invisíveis de Hover por Período */}
            {points.map((p, idx) => {
              const x = chartMetrics.getX(idx);
              const sliceWidth = chartMetrics.chartW / Math.max(1, points.length - 1);
              return (
                <rect
                  key={`hover-${p.id}`}
                  x={x - sliceWidth / 2}
                  y={chartMetrics.padding.top}
                  width={sliceWidth}
                  height={chartMetrics.chartH}
                  fill="transparent"
                  className="cursor-pointer"
                  onMouseEnter={() => setHoveredPointIndex(idx)}
                />
              );
            })}
          </svg>

          {/* Tooltip de Detalhes do Ponto Selecionado */}
          {hoveredPointIndex !== null && points[hoveredPointIndex] && (
            <div className="mt-2 rounded-lg bg-neutral-900 text-white p-3 text-xs shadow-lg flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-blue-400">
                  Período: {points[hoveredPointIndex].period_label}
                </span>
                <span className="text-neutral-400">({config.unitLabel})</span>
              </div>
              <div className="flex flex-wrap gap-4">
                <div>
                  <span className="text-neutral-400 block text-[10px]">
                    {isFixtureMode ? "REALIZADO (FIXTURE)" : "REALIZADO"}
                  </span>
                  <span className="font-bold text-white">
                    {fmtVal(points[hoveredPointIndex].actual_value)}
                  </span>
                </div>
                <div>
                  <span className="text-neutral-400 block text-[10px]">TARGET (META)</span>
                  <span className="font-bold text-emerald-400">
                    {fmtVal(points[hoveredPointIndex].target_value)}
                  </span>
                </div>
                <div>
                  <span className="text-neutral-400 block text-[10px]">FORECAST (PROJEÇÃO)</span>
                  <span className="font-bold text-blue-400">
                    {fmtVal(points[hoveredPointIndex].forecast_value)}
                    {points[hoveredPointIndex].forecast_lower !== null && (
                      <span className="text-[10px] text-neutral-400 ml-1 font-normal">
                        [{fmtVal(points[hoveredPointIndex].forecast_lower)} - {fmtVal(points[hoveredPointIndex].forecast_upper)}]
                      </span>
                    )}
                  </span>
                </div>
                <div>
                  <span className="text-neutral-400 block text-[10px]">BASELINE</span>
                  <span className="font-bold text-neutral-300">
                    {fmtVal(points[hoveredPointIndex].baseline_value)}
                  </span>
                </div>
                <div>
                  <span className="text-neutral-400 block text-[10px]">CONTINUIDADE</span>
                  <span className="font-bold text-amber-400">
                    {fmtVal(points[hoveredPointIndex].continuity_value)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tabela de Desvios Analíticos */}
      <div className="mt-6">
        <button
          onClick={() => setShowTable(!showTable)}
          className="flex items-center gap-2 text-xs font-semibold text-neutral-700 hover:text-neutral-900 transition-colors"
        >
          <span>{showTable ? "▼ Ocultar matriz analítica de desvios" : "▶ Exibir matriz analítica de desvios"}</span>
        </button>

        {showTable && (
          <div className="mt-3 overflow-x-auto rounded-lg border border-neutral-200">
            <table className="min-w-full divide-y divide-neutral-200 text-left text-xs">
              <thead className="bg-neutral-50 text-neutral-700">
                <tr>
                  <th scope="col" className="px-3.5 py-2.5 font-bold">Período</th>
                  <th scope="col" className="px-3.5 py-2.5 font-bold">Realizado</th>
                  <th scope="col" className="px-3.5 py-2.5 font-bold">Target</th>
                  <th scope="col" className="px-3.5 py-2.5 font-bold">Δ Realizado vs. Target</th>
                  <th scope="col" className="px-3.5 py-2.5 font-bold">Forecast</th>
                  <th scope="col" className="px-3.5 py-2.5 font-bold">Δ Realizado vs. Forecast</th>
                  <th scope="col" className="px-3.5 py-2.5 font-bold">Continuidade</th>
                  <th scope="col" className="px-3.5 py-2.5 font-bold">Status Metodológico</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200 bg-white">
                {points.map((p) => {
                  const deltaTarget = fmtDelta(p.actual_value, p.target_value);
                  const deltaForecast = fmtDelta(p.actual_value, p.forecast_value);
                  const isOfficial = !isFixtureMode && p.calibration_status === "official";
                  const statusLabel = isFixtureMode
                    ? "Sintético (Fixture)"
                    : (isOfficial ? "Oficial verificado" : "Ilustrativo / Em calibração");
                  const statusClass = isFixtureMode
                    ? "bg-amber-50 text-amber-800 border border-amber-200"
                    : (isOfficial
                      ? "bg-neutral-100 text-neutral-800 border border-neutral-300"
                      : "bg-blue-50 text-blue-800 border border-blue-200");

                  return (
                    <tr key={p.id} className="hover:bg-neutral-50 transition-colors">
                      <td className="px-3.5 py-2 font-bold text-neutral-900">{p.period_label}</td>
                      <td className="px-3.5 py-2 font-semibold text-neutral-900">
                        {fmtVal(p.actual_value)}
                      </td>
                      <td className="px-3.5 py-2 text-neutral-700">
                        {fmtVal(p.target_value)}
                      </td>
                      <td className={`px-3.5 py-2 font-medium ${deltaTarget !== "—" ? "text-neutral-900" : "text-neutral-400"}`}>
                        {deltaTarget}
                      </td>
                      <td className="px-3.5 py-2 text-blue-700 font-medium">
                        {fmtVal(p.forecast_value)}
                      </td>
                      <td className={`px-3.5 py-2 font-medium ${deltaForecast !== "—" ? "text-neutral-900" : "text-neutral-400"}`}>
                        {deltaForecast}
                      </td>
                      <td className="px-3.5 py-2 text-amber-700">
                        {fmtVal(p.continuity_value)}
                      </td>
                      <td className="px-3.5 py-2">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${statusClass}`}
                        >
                          {statusLabel}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Nota Constitucional e Salvaguarda Metodológica */}
      <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50/60 p-3.5 text-xs text-amber-900">
        <p className="font-semibold flex items-center gap-1.5">
          <svg className="w-4 h-4 text-amber-700" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          Salvaguarda Constitucional (specs/mission.md & AGENTS.md):
        </p>
        <p className="mt-1 leading-relaxed text-amber-800">
          Projeções (Forecasts) e cenários contrafactuais são modelos econométricos e estimativas de mercado experimentais, marcadas expressamente como <strong>Ilustrativas</strong> até ratificação e auditoria humana independente. Desvios numéricos representam grandezas matemáticas entre métricas e premissas, sem atribuição causal prematura ou julgamento de valor político. Em modo demonstrador (fixture), nenhum valor histórico ou projetado deve ser interpretado como estatística pública oficial.
        </p>
      </div>
    </section>
  );
}
