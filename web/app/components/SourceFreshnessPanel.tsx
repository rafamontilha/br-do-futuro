"use client";

import React, { useState } from "react";
import { OperationalReplayModal } from "./OperationalReplayModal";

export interface SourceSchedule {
  id: string;
  indicator_id: string;
  primary_source: string;
  fallback_source?: string | null;
  cron_expression: string;
  frequency: string;
  expected_release_day_offset: number;
  expected_release_time: string;
  tolerance_window_hours: number;
  last_checked_at?: string | null;
  last_successful_at?: string | null;
  next_expected_at: string;
  is_stale: boolean;
  current_delay_hours: number | string;
  consecutive_failures: number;
  circuit_open: boolean;
  metadata?: Record<string, any>;
  updated_at?: string;
}

interface SourceFreshnessPanelProps {
  initialSchedules?: SourceSchedule[];
}

const defaultSchedules: SourceSchedule[] = [
  {
    id: "sched-ipca",
    indicator_id: "br.ipca.monthly",
    primary_source: "IBGE_SIDRA",
    fallback_source: "BCB_SGS",
    cron_expression: "0 9 10 * *",
    frequency: "monthly",
    expected_release_day_offset: 10,
    expected_release_time: "09:00:00",
    tolerance_window_hours: 4,
    next_expected_at: "2026-11-10T09:00:00-03:00",
    is_stale: false,
    current_delay_hours: 0.0,
    consecutive_failures: 0,
    circuit_open: false,
    metadata: { agency: "IBGE", sidra_table: 1737 },
  },
  {
    id: "sched-selic",
    indicator_id: "br.selic.daily",
    primary_source: "BCB_SGS",
    fallback_source: null,
    cron_expression: "0 9 * * 1-5",
    frequency: "daily",
    expected_release_day_offset: 1,
    expected_release_time: "09:00:00",
    tolerance_window_hours: 4,
    next_expected_at: "2026-10-30T09:00:00-03:00",
    is_stale: false,
    current_delay_hours: 0.0,
    consecutive_failures: 0,
    circuit_open: false,
    metadata: { agency: "BCB", sgs_code: 11 },
  },
  {
    id: "sched-debt",
    indicator_id: "br.debt.gross_pct_gdp",
    primary_source: "BCB_SGS",
    fallback_source: null,
    cron_expression: "0 9 30 * *",
    frequency: "monthly",
    expected_release_day_offset: 30,
    expected_release_time: "09:30:00",
    tolerance_window_hours: 6,
    next_expected_at: "2026-10-31T09:30:00-03:00",
    is_stale: false,
    current_delay_hours: 0.0,
    consecutive_failures: 0,
    circuit_open: false,
    metadata: { agency: "BCB", sgs_code: 13762 },
  },
];

export function SourceFreshnessPanel({ initialSchedules }: SourceFreshnessPanelProps) {
  const [schedules] = useState<SourceSchedule[]>(
    initialSchedules && initialSchedules.length > 0 ? initialSchedules : defaultSchedules,
  );
  const [isModalOpen, setIsModalOpen] = useState(false);

  function formatDate(isoStr?: string | null) {
    if (!isoStr) return "Nenhuma captura registrada";
    try {
      const d = new Date(isoStr);
      return new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(d);
    } catch {
      return isoStr;
    }
  }

  return (
    <section style={{ margin: "48px 0" }}>
      <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <h2>Saúde Operacional & Freshness das Fontes</h2>
          <span style={{ fontSize: "11px", letterSpacing: "1px", color: "var(--muted, #52675d)" }}>
            SLO DE DADOS & RASTREABILIDADE TEMPORAL
          </span>
        </div>
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          style={{
            background: "var(--green, #216044)",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            padding: "8px 16px",
            fontSize: "12px",
            fontWeight: "bold",
            cursor: "pointer",
            letterSpacing: "0.5px",
          }}
        >
          Disparar Replay Operacional
        </button>
      </div>

      <p style={{ color: "var(--muted, #52675d)", fontSize: "14px", marginTop: "8px", marginBottom: "24px" }}>
        Acompanhamento de conformidade entre os cronogramas oficiais de publicação e a captura real.
        A defasagem tolerada protege contra alarmes falsos em janelas normais de divulgação.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "20px",
        }}
      >
        {schedules.map((s) => {
          const delayNum = Number(s.current_delay_hours) || 0;
          let slaBadge = { label: "EM DIA", bg: "#e8f5e9", color: "#1b5e20", border: "#a5d6a7" };

          if (s.is_stale) {
            slaBadge = { label: `ATRASADO (+${delayNum}h)`, bg: "#ffebee", color: "#b71c1c", border: "#ef9a9a" };
          } else if (delayNum > 0) {
            slaBadge = { label: `ATENÇÃO (+${delayNum}h)`, bg: "#fff8e1", color: "#f57f17", border: "#ffe082" };
          }

          return (
            <div
              key={s.id}
              style={{
                background: "#fff",
                border: "1px solid var(--line, #d5dccf)",
                borderRadius: "6px",
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <span
                    style={{
                      fontFamily: "monospace",
                      fontSize: "12px",
                      background: "#f0f2ed",
                      padding: "3px 8px",
                      borderRadius: "4px",
                      color: "var(--ink, #15342d)",
                    }}
                  >
                    {s.indicator_id}
                  </span>
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: "bold",
                      padding: "4px 8px",
                      borderRadius: "12px",
                      background: slaBadge.bg,
                      color: slaBadge.color,
                      border: `1px solid ${slaBadge.border}`,
                    }}
                  >
                    {slaBadge.label}
                  </span>
                </div>

                <div style={{ fontSize: "13px", lineHeight: "1.7", color: "var(--ink, #15342d)" }}>
                  <div>
                    <strong>Fonte Primária:</strong> <code>{s.primary_source}</code>
                  </div>
                  {s.fallback_source && (
                    <div>
                      <strong>Contingência:</strong> <code>{s.fallback_source}</code>
                    </div>
                  )}
                  <div>
                    <strong>Próxima Divulgação:</strong> {formatDate(s.next_expected_at)}
                  </div>
                  <div>
                    <strong>Última Coleta:</strong> {formatDate(s.last_successful_at)}
                  </div>
                  <div>
                    <strong>Janela de Tolerância:</strong> {s.tolerance_window_hours}h
                  </div>
                </div>
              </div>

              <div
                style={{
                  marginTop: "16px",
                  paddingTop: "12px",
                  borderTop: "1px solid var(--line, #d5dccf)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: "11px",
                }}
              >
                <span style={{ color: "var(--muted, #52675d)" }}>
                  Falhas consecutivas: <strong>{s.consecutive_failures}</strong>
                </span>
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: "4px",
                    fontWeight: "600",
                    background: s.circuit_open ? "#ffebee" : "#e8f5e9",
                    color: s.circuit_open ? "#c62828" : "#2e7d32",
                  }}
                >
                  {s.circuit_open ? "Circuito Aberto" : "Circuito Fechado (Normal)"}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <OperationalReplayModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </section>
  );
}
