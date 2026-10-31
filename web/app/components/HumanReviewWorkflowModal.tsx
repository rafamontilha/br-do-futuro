"use client";

import React, { useState } from "react";

export interface AlertItem {
  id: string;
  scenario_run_id: string;
  severity: string;
  owner_role: string;
  sla_hours: number;
  status: string;
  review_status: string;
  evidence: {
    delta_pp?: string;
    threshold_pp?: string;
    rule?: string;
    target_breach?: boolean;
    current_debt_pct?: string;
    scenario_id?: string;
  };
  reviewed_by?: string;
  review_justification?: string;
  reviewed_at?: string;
  created_at?: string;
}

interface HumanReviewWorkflowModalProps {
  alert: AlertItem | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function HumanReviewWorkflowModal({
  alert,
  isOpen,
  onClose,
  onSuccess,
}: HumanReviewWorkflowModalProps) {
  const [action, setAction] = useState<"approve" | "reject">("approve");
  const [justification, setJustification] = useState("");
  const [apiKey, setApiKey] = useState("bdf-reviewer-token-2026");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string; details?: any } | null>(null);

  if (!isOpen || !alert) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (justification.trim().length < 15) {
      setFeedback({
        type: "error",
        message: "A justificativa técnica deve conter no mínimo 15 caracteres.",
      });
      return;
    }

    setSubmitting(true);
    setFeedback(null);

    try {
      const res = await fetch(`/api/v1/alerts/${alert.id}/review`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey.trim(),
        },
        body: JSON.stringify({
          action,
          justification: justification.trim(),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setFeedback({
          type: "error",
          message: data.error || "Falha ao registrar revisão humana.",
        });
      } else {
        setFeedback({
          type: "success",
          message: `Alerta ${action === "approve" ? "aprovado" : "rejeitado"} com sucesso e registrado na trilha imutável de auditoria.`,
          details: data.data,
        });
        setTimeout(() => {
          onSuccess();
          onClose();
        }, 2000);
      }
    } catch (err: any) {
      setFeedback({
        type: "error",
        message: "Erro de conexão ao submeter revisão.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const isAlreadyReviewed = alert.review_status !== "pending_human_review";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-modal-title"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(10, 20, 15, 0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "16px",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "#ffffff",
          borderRadius: "10px",
          maxWidth: "640px",
          width: "100%",
          maxHeight: "90vh",
          overflowY: "auto",
          padding: "24px 28px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)",
          border: "1px solid #d1dbd6",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            borderBottom: "1px solid #e5eae7",
            paddingBottom: "16px",
            marginBottom: "20px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 800,
                  textTransform: "uppercase",
                  background: isAlreadyReviewed ? "#def0e5" : "#fee2e2",
                  color: isAlreadyReviewed ? "#1a5e3a" : "#b91c1c",
                  padding: "2px 8px",
                  borderRadius: "4px",
                }}
              >
                {isAlreadyReviewed ? "Revisão Concluída" : "Revisão Humana Obrigatória"}
              </span>
              <span style={{ fontSize: "12px", color: "var(--muted, #52675d)" }}>
                SLA: {alert.sla_hours}h · Papel: {alert.owner_role}
              </span>
            </div>
            <h2 id="review-modal-title" style={{ fontSize: "19px", fontWeight: 700, margin: "6px 0 0 0" }}>
              Workflow de Homologação de Impacto Material
            </h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Fechar modal"
            style={{
              background: "transparent",
              border: "none",
              fontSize: "24px",
              cursor: "pointer",
              color: "#52675d",
            }}
          >
            ×
          </button>
        </div>

        {/* Detalhes da Evidência do Alerta */}
        <div
          style={{
            background: "#f8faf9",
            border: "1px solid #e1e8e5",
            borderRadius: "6px",
            padding: "14px 16px",
            marginBottom: "20px",
            fontSize: "13px",
            lineHeight: 1.5,
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "8px" }}>
            <div>
              <span style={{ color: "var(--muted, #52675d)", fontSize: "11.5px" }}>ID do Alerta:</span>
              <div style={{ fontFamily: "monospace", fontWeight: 600, fontSize: "12px" }}>{alert.id.slice(0, 18)}...</div>
            </div>
            <div>
              <span style={{ color: "var(--muted, #52675d)", fontSize: "11.5px" }}>Cenário / Modelo:</span>
              <div style={{ fontWeight: 600 }}>{alert.evidence?.scenario_id || "Identidade Fiscal v1"}</div>
            </div>
            <div>
              <span style={{ color: "var(--muted, #52675d)", fontSize: "11.5px" }}>Variação Absoluta (Δ):</span>
              <div style={{ fontWeight: 700, color: "#b91c1c", fontSize: "14px" }}>
                {alert.evidence?.delta_pp ? `${alert.evidence.delta_pp} p.p.` : "N/A"}
              </div>
            </div>
            <div>
              <span style={{ color: "var(--muted, #52675d)", fontSize: "11.5px" }}>Limiar Experimental:</span>
              <div style={{ fontWeight: 600 }}>{alert.evidence?.threshold_pp || "0.5"} p.p.</div>
            </div>
          </div>
          {alert.evidence?.target_breach && (
            <div
              style={{
                marginTop: "8px",
                padding: "6px 10px",
                background: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "4px",
                color: "#991b1b",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              ⚠️ Violação de Meta Institucional: Nova trajetória ultrapassa a banda de tolerância oficial (80% PIB).
            </div>
          )}
        </div>

        {isAlreadyReviewed ? (
          <div
            style={{
              padding: "14px 16px",
              background: "#def0e5",
              border: "1px solid #bbf7d0",
              borderRadius: "6px",
              marginBottom: "16px",
              fontSize: "13px",
            }}
          >
            <strong>Status Atual:</strong> {alert.review_status === "approved" ? "Aprovado por Revisor Independente" : "Rejeitado"}<br />
            {alert.reviewed_by && <><strong>Revisor:</strong> {alert.reviewed_by}<br /></>}
            {alert.reviewed_at && <><strong>Data da Revisão:</strong> {new Date(alert.reviewed_at).toLocaleString("pt-BR")}<br /></>}
            {alert.review_justification && <><strong>Justificativa Técnica:</strong> {alert.review_justification}</>}
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "block", fontSize: "12.5px", fontWeight: 700, marginBottom: "6px" }}>
                Decisão da Revisão Metodológica:
              </label>
              <div style={{ display: "flex", gap: "12px" }}>
                <label
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    border: `1.5px solid ${action === "approve" ? "#16a34a" : "#d1dbd6"}`,
                    background: action === "approve" ? "#f0fdf4" : "#ffffff",
                    cursor: "pointer",
                    fontSize: "13px",
                    fontWeight: 600,
                  }}
                >
                  <input
                    type="radio"
                    name="review_action"
                    value="approve"
                    checked={action === "approve"}
                    onChange={() => setAction("approve")}
                  />
                  Aprovar Impacto Material
                </label>
                <label
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    border: `1.5px solid ${action === "reject" ? "#dc2626" : "#d1dbd6"}`,
                    background: action === "reject" ? "#fef2f2" : "#ffffff",
                    cursor: "pointer",
                    fontSize: "13px",
                    fontWeight: 600,
                  }}
                >
                  <input
                    type="radio"
                    name="review_action"
                    value="reject"
                    checked={action === "reject"}
                    onChange={() => setAction("reject")}
                  />
                  Rejeitar / Reclassificar
                </label>
              </div>
            </div>

            <div style={{ marginBottom: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <label style={{ fontSize: "12.5px", fontWeight: 700 }}>
                  Justificativa Técnica Formal (Obrigatória):
                </label>
                <span
                  style={{
                    fontSize: "11px",
                    color: justification.trim().length >= 15 ? "#16a34a" : "#dc2626",
                    fontWeight: 600,
                  }}
                >
                  {justification.trim().length} / 15 caracteres mínimos
                </span>
              </div>
              <textarea
                rows={3}
                required
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                placeholder="Exemplo: Revisão metodológica concluída; desvio de premissas consistente com a publicação de novas estatísticas fiscais oficiais."
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: "6px",
                  border: "1px solid #d1dbd6",
                  fontSize: "13px",
                  lineHeight: 1.4,
                  resize: "vertical",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div style={{ marginBottom: "20px" }}>
              <label style={{ display: "block", fontSize: "12px", color: "var(--muted, #52675d)", marginBottom: "4px" }}>
                Chave de API do Revisor (X-API-Key com perfil reviewer ou publisher):
              </label>
              <input
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  borderRadius: "4px",
                  border: "1px solid #d1dbd6",
                  fontSize: "12px",
                  fontFamily: "monospace",
                  background: "#f8faf9",
                  boxSizing: "border-box",
                }}
              />
            </div>

            {feedback && (
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: "6px",
                  marginBottom: "16px",
                  fontSize: "12.5px",
                  background: feedback.type === "success" ? "#def0e5" : "#fee2e2",
                  color: feedback.type === "success" ? "#1a5e3a" : "#b91c1c",
                  border: `1px solid ${feedback.type === "success" ? "#bbf7d0" : "#fecaca"}`,
                }}
              >
                {feedback.message}
                {feedback.details?.audit_id && (
                  <div style={{ fontSize: "11.5px", marginTop: "4px", fontFamily: "monospace" }}>
                    Registro de Auditoria: {feedback.details.audit_id}
                  </div>
                )}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button
                type="button"
                onClick={onClose}
                disabled={submitting}
                style={{
                  background: "#f1f5f9",
                  border: "1px solid #cbd5e1",
                  borderRadius: "6px",
                  padding: "8px 16px",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={submitting || justification.trim().length < 15}
                style={{
                  background: action === "approve" ? "#15803d" : "#b91c1c",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "6px",
                  padding: "8px 20px",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: submitting || justification.trim().length < 15 ? "not-allowed" : "pointer",
                  opacity: submitting || justification.trim().length < 15 ? 0.65 : 1,
                }}
              >
                {submitting ? "Gravando na Auditoria..." : action === "approve" ? "Homologar e Liberar" : "Confirmar Rejeição"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
