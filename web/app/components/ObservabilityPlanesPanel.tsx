"use client";

import React, { useState } from "react";
import { RoleType } from "./RoleSwitcherBadge";
import { DecisionAuditTrailModal } from "./DecisionAuditTrailModal";

export interface ObservabilityData {
  timestamp: string;
  platform: {
    uptime_seconds: number;
    database_status: string;
    error_rate_pct?: number | null;
    p95_latency_ms?: number | null;
  };
  data: {
    tracked_series_count: number;
    stale_series_count: number;
    quarantine_count: number;
    last_ingestion_at?: string | null;
  };
  models: {
    active_scenarios_count: number;
    calibrated_parameters_count: number;
    last_simulation_at?: string | null;
  };
  decisions: {
    total_decisions_count: number;
    pending_reviews_count: number;
    audit_chain_intact?: boolean | null;
  };
  slo_compliance: {
    source_window_compliance_pct?: number | null;
    metadata_completeness_pct?: number | null;
    scenario_lineage_coverage_pct?: number | null;
    reproducible_forecasts_pct?: number | null;
  };
}

interface ObservabilityPlanesPanelProps {
  currentRole: RoleType;
  initialMetrics?: ObservabilityData;
}

const unmeasuredObservabilityData: ObservabilityData = {
  timestamp: new Date().toISOString(),
  platform: {
    uptime_seconds: 0,
    database_status: "unconfigured",
    error_rate_pct: null,
    p95_latency_ms: null,
  },
  data: {
    tracked_series_count: 0,
    stale_series_count: 0,
    quarantine_count: 0,
    last_ingestion_at: null,
  },
  models: {
    active_scenarios_count: 0,
    calibrated_parameters_count: 0,
    last_simulation_at: null,
  },
  decisions: {
    total_decisions_count: 0,
    pending_reviews_count: 0,
    audit_chain_intact: null,
  },
  slo_compliance: {
    source_window_compliance_pct: null,
    metadata_completeness_pct: null,
    scenario_lineage_coverage_pct: null,
    reproducible_forecasts_pct: null,
  },
};

export function ObservabilityPlanesPanel({
  currentRole,
  initialMetrics,
}: ObservabilityPlanesPanelProps) {
  const [metrics] = useState<ObservabilityData>(initialMetrics || unmeasuredObservabilityData);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);

  const formatUptime = (seconds: number) => {
    if (!seconds || seconds <= 0) return "0m";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;
  };

  const isHealthy = metrics.platform.database_status === "healthy";

  return (
    <section
      style={{
        margin: "36px 0",
        background: "#ffffff",
        border: "1px solid #d1dbd6",
        borderRadius: "8px",
        padding: "24px",
      }}
      aria-label="Observabilidade dos Quatro Planos e Resiliência Operacional"
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px", marginBottom: "20px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ margin: 0, fontSize: "19px", color: "var(--ink, #15342d)" }}>
              Observabilidade dos Quatro Planos & Resiliência
            </h2>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                background: "#def0e5",
                color: "#166534",
                padding: "2px 8px",
                borderRadius: "4px",
              }}
            >
              Incremento 04
            </span>
          </div>
          <p style={{ margin: "6px 0 0 0", fontSize: "13px", color: "var(--muted, #52675d)" }}>
            Telemetria unificada de Plataforma, Dados, Modelos e Decisões derivada de evidências operacionais.
          </p>
        </div>

        <button
          onClick={() => setIsAuditModalOpen(true)}
          style={{
            fontSize: "12.5px",
            fontWeight: 700,
            padding: "8px 16px",
            background: "#15342d",
            color: "#ffffff",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            boxShadow: "0 2px 4px rgba(0,0,0,0.08)",
          }}
        >
          <span>📜</span>
          <span>Inspecionar Trilha de Auditoria</span>
        </button>
      </div>

      {/* Grid dos 4 Planos */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        {/* Plano de Plataforma */}
        <div style={{ background: "#f8faf9", border: "1px solid #e2e8f0", borderRadius: "6px", padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "11px", fontWeight: 800, textTransform: "uppercase", color: "#1d5d85" }}>
              1. Plataforma
            </span>
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: isHealthy ? "#16a34a" : "#f59e0b",
              }}
            />
          </div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--ink, #15342d)", marginBottom: "4px" }}>
            {formatUptime(metrics.platform.uptime_seconds)}
          </div>
          <div style={{ fontSize: "11.5px", color: "var(--muted, #52675d)", lineHeight: "1.5" }}>
            Status banco: <strong>{metrics.platform.database_status}</strong> • Latência p95: <strong>{metrics.platform.p95_latency_ms != null ? `${metrics.platform.p95_latency_ms} ms` : "Não aferido"}</strong> • Taxa de erro: <strong>{metrics.platform.error_rate_pct != null ? `${metrics.platform.error_rate_pct}%` : "Não aferido"}</strong>
          </div>
        </div>

        {/* Plano de Dados */}
        <div style={{ background: "#f8faf9", border: "1px solid #e2e8f0", borderRadius: "6px", padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "11px", fontWeight: 800, textTransform: "uppercase", color: "#85581d" }}>
              2. Dados & Contratos
            </span>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#16a34a" }} />
          </div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--ink, #15342d)", marginBottom: "4px" }}>
            {metrics.data.tracked_series_count} Séries / Contratos
          </div>
          <div style={{ fontSize: "11.5px", color: "var(--muted, #52675d)", lineHeight: "1.5" }}>
            {metrics.data.stale_series_count} séries com atraso • <strong>{metrics.data.quarantine_count}</strong> em quarentena
          </div>
        </div>

        {/* Plano de Modelos */}
        <div style={{ background: "#f8faf9", border: "1px solid #e2e8f0", borderRadius: "6px", padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "11px", fontWeight: 800, textTransform: "uppercase", color: "#6b21a8" }}>
              3. Modelos & Cenários
            </span>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#16a34a" }} />
          </div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--ink, #15342d)", marginBottom: "4px" }}>
            {metrics.models.active_scenarios_count} Cenários Ativos
          </div>
          <div style={{ fontSize: "11.5px", color: "var(--muted, #52675d)", lineHeight: "1.5" }}>
            <strong>{metrics.models.calibrated_parameters_count}</strong> parâmetros fiscais calibrados
          </div>
        </div>

        {/* Plano de Decisões */}
        <div style={{ background: "#f8faf9", border: "1px solid #e2e8f0", borderRadius: "6px", padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "11px", fontWeight: 800, textTransform: "uppercase", color: "#166534" }}>
              4. Decisões & Auditoria
            </span>
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: metrics.decisions.audit_chain_intact === true ? "#16a34a" : metrics.decisions.audit_chain_intact === false ? "#dc2626" : "#94a3b8",
              }}
            />
          </div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--ink, #15342d)", marginBottom: "4px" }}>
            {metrics.decisions.total_decisions_count} Decisões
          </div>
          <div style={{ fontSize: "11.5px", color: "var(--muted, #52675d)", lineHeight: "1.5" }}>
            Cadeia SHA-256: <strong>{metrics.decisions.audit_chain_intact === true ? "Íntegra" : metrics.decisions.audit_chain_intact === false ? "Violação Detectada" : "Não aferida"}</strong> • {metrics.decisions.pending_reviews_count} revisões pendentes
          </div>
        </div>
      </div>

      {/* Tabela de SLOs Mensurados */}
      <div style={{ border: "1px solid #e2e8f0", borderRadius: "6px", overflow: "hidden" }}>
        <div style={{ background: "#f1f5f3", padding: "10px 16px", fontSize: "12px", fontWeight: 700, color: "var(--ink, #15342d)" }}>
          Métricas de Nível de Serviço (SLOs Constitucionais Mensurados)
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1px", background: "#e2e8f0" }}>
          <div style={{ background: "#ffffff", padding: "12px 16px" }}>
            <div style={{ fontSize: "11px", color: "var(--muted, #52675d)" }}>Janela de Fonte</div>
            <div style={{ fontSize: "16px", fontWeight: 700, color: metrics.slo_compliance.source_window_compliance_pct != null ? "#166534" : "#64748b" }}>
              {metrics.slo_compliance.source_window_compliance_pct != null ? `${metrics.slo_compliance.source_window_compliance_pct}%` : "Aguardando coletas"}
            </div>
            <div style={{ fontSize: "10px", color: "#64748b" }}>Meta: ≥ 99.0%</div>
          </div>
          <div style={{ background: "#ffffff", padding: "12px 16px" }}>
            <div style={{ fontSize: "11px", color: "var(--muted, #52675d)" }}>Metadados Públicos</div>
            <div style={{ fontSize: "16px", fontWeight: 700, color: metrics.slo_compliance.metadata_completeness_pct != null ? "#166534" : "#64748b" }}>
              {metrics.slo_compliance.metadata_completeness_pct != null ? `${metrics.slo_compliance.metadata_completeness_pct}%` : "Aguardando coletas"}
            </div>
            <div style={{ fontSize: "10px", color: "#64748b" }}>Meta: 100%</div>
          </div>
          <div style={{ background: "#ffffff", padding: "12px 16px" }}>
            <div style={{ fontSize: "11px", color: "var(--muted, #52675d)" }}>Rastreabilidade Cenários</div>
            <div style={{ fontSize: "16px", fontWeight: 700, color: metrics.slo_compliance.scenario_lineage_coverage_pct != null ? "#166534" : "#64748b" }}>
              {metrics.slo_compliance.scenario_lineage_coverage_pct != null ? `${metrics.slo_compliance.scenario_lineage_coverage_pct}%` : "Aguardando coletas"}
            </div>
            <div style={{ fontSize: "10px", color: "#64748b" }}>Meta: 100%</div>
          </div>
          <div style={{ background: "#ffffff", padding: "12px 16px" }}>
            <div style={{ fontSize: "11px", color: "var(--muted, #52675d)" }}>Reprodutibilidade Forecasts</div>
            <div style={{ fontSize: "16px", fontWeight: 700, color: metrics.slo_compliance.reproducible_forecasts_pct != null ? "#166534" : "#64748b" }}>
              {metrics.slo_compliance.reproducible_forecasts_pct != null ? `${metrics.slo_compliance.reproducible_forecasts_pct}%` : "Aguardando coletas"}
            </div>
            <div style={{ fontSize: "10px", color: "#64748b" }}>Meta: 100%</div>
          </div>
        </div>
      </div>

      {/* Modal de Auditoria */}
      <DecisionAuditTrailModal
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
        currentRole={currentRole}
      />
    </section>
  );
}
