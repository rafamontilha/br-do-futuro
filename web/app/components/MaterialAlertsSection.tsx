"use client";

import React, { useState } from "react";
import { DependencyGraphVisualizer } from "./DependencyGraphVisualizer";
import { HumanReviewWorkflowModal, type AlertItem } from "./HumanReviewWorkflowModal";

interface MaterialAlertsSectionProps {
  initialAlerts?: AlertItem[];
  mode?: string;
}

export function MaterialAlertsSection({
  initialAlerts = [],
  mode = "fixture",
}: MaterialAlertsSectionProps) {
  const [alerts, setAlerts] = useState<AlertItem[]>(initialAlerts);
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [isDAGModalOpen, setIsDAGModalOpen] = useState(false);

  const refreshAlerts = async () => {
    try {
      const res = await fetch(`/api/v1/alerts?mode=${mode}`);
      if (res.ok) {
        const payload = await res.json();
        if (payload?.data) {
          setAlerts(payload.data);
        }
      }
    } catch (err) {
      console.error("Failed to refresh alerts:", err);
    }
  };

  const handleOpenReview = (alert: AlertItem) => {
    setSelectedAlert(alert);
    setIsReviewModalOpen(true);
  };

  return (
    <section aria-labelledby="human-review-title">
      <div className="section-title">
        <h2 id="human-review-title">Revisão humana & Materialidade</h2>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button
            type="button"
            onClick={() => setIsDAGModalOpen(true)}
            style={{
              background: "#e3f0f7",
              color: "#1d5d85",
              border: "1px solid #93c5e0",
              borderRadius: "4px",
              padding: "4px 10px",
              fontSize: "11px",
              fontWeight: 700,
              cursor: "pointer",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            Ver Grafo de Dependências (DAG)
          </button>
          <span>PUBLICAÇÃO MATERIAL CONDICIONADA</span>
        </div>
      </div>

      <p style={{ margin: "4px 0 16px 0", fontSize: "13px", color: "var(--muted, #52675d)", lineHeight: 1.5 }}>
        O motor de dependências avalia o impacto conjunto de novas publicações nos modelos. Variações absolutas superiores a 0,5 p.p. na trajetória fiscal ou rupturas de metas institucionais bloqueiam a publicação automática até homologação técnica por revisor independente com registro na trilha de auditoria.
      </p>

      {alerts.length ? (
        <ul className="alerts" style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "10px" }}>
          {alerts.map((a) => {
            const isPending = a.review_status === "pending_human_review";
            const isApproved = a.review_status === "approved";
            const deltaValue = a.evidence?.delta_pp ? Number(a.evidence.delta_pp) : 0;
            const formattedDelta = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(deltaValue);

            return (
              <li
                key={a.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "12px",
                  padding: "14px 18px",
                  background: isPending ? "#fff" : isApproved ? "#f0fdf4" : "#fef2f2",
                  border: `1.5px solid ${isPending ? "#fca5a5" : isApproved ? "#86efac" : "#fecaca"}`,
                  borderRadius: "6px",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <strong style={{ fontSize: "14px", color: "#111827" }}>
                      Impacto material: {formattedDelta} p.p.
                    </strong>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: "4px",
                        background: isPending ? "#fee2e2" : isApproved ? "#dcfce7" : "#fee2e2",
                        color: isPending ? "#991b1b" : isApproved ? "#166534" : "#991b1b",
                      }}
                    >
                      {isPending
                        ? "Aguardando Revisão Humana"
                        : isApproved
                        ? "Aprovado por Revisor Independente"
                        : "Rejeitado"}
                    </span>
                    {a.evidence?.target_breach && (
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "4px",
                          background: "#fef3c7",
                          color: "#92400e",
                        }}
                      >
                        Ruptura de Meta
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--muted, #52675d)", marginTop: "4px" }}>
                    Limiar experimental: {a.evidence?.threshold_pp || "0,5"} p.p. · SLA: {a.sla_hours}h · Papel: {a.owner_role}
                    {a.reviewed_by && (
                      <span style={{ marginLeft: "6px" }}>
                        · Homologado por: <strong>{a.reviewed_by}</strong>
                      </span>
                    )}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleOpenReview(a)}
                  style={{
                    background: isPending ? "#1d5d85" : "#f1f5f9",
                    color: isPending ? "#ffffff" : "#334155",
                    border: `1px solid ${isPending ? "#1d5d85" : "#cbd5e1"}`,
                    borderRadius: "6px",
                    padding: "6px 14px",
                    fontSize: "12.5px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {isPending ? "Revisar Alerta" : "Ver Decisão / Justificativa"}
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="empty">Nenhum alerta material registrado neste modo.</p>
      )}

      {/* Modais Interativos */}
      <DependencyGraphVisualizer
        isOpen={isDAGModalOpen}
        onClose={() => setIsDAGModalOpen(false)}
      />

      <HumanReviewWorkflowModal
        alert={selectedAlert}
        isOpen={isReviewModalOpen}
        onClose={() => {
          setIsReviewModalOpen(false);
          setSelectedAlert(null);
        }}
        onSuccess={refreshAlerts}
      />
    </section>
  );
}
