"use client";

import React, { useState, useEffect } from "react";
import { RoleType, ROLES } from "./RoleSwitcherBadge";

export interface DecisionAuditRecord {
  id: string;
  event_id?: string | null;
  actor_id: string;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  justification: string;
  previous_state?: Record<string, any> | null;
  new_state: Record<string, any>;
  payload_hash: string;
  prev_log_hash: string;
  created_at: string;
}

interface DecisionAuditTrailModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentRole: RoleType;
  initialRecords?: DecisionAuditRecord[];
}

export function DecisionAuditTrailModal({
  isOpen,
  onClose,
  currentRole,
  initialRecords,
}: DecisionAuditTrailModalProps) {
  const [records, setRecords] = useState<DecisionAuditRecord[]>(initialRecords || []);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [action, setAction] = useState("approve_calibration");
  const [entityType, setEntityType] = useState("fiscal_calibration");
  const [entityId, setEntityId] = useState("calib-primary-surplus-v1");
  const [justification, setJustification] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);

  const roleConfig = ROLES[currentRole];
  const canAccessAudit = currentRole === "reviewer" || currentRole === "publisher";

  const fetchRecords = async () => {
    if (!canAccessAudit) {
      setRecords([]);
      setFetchError(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setFetchError(null);

    try {
      const res = await fetch("/api/v1/admin/audit/decisions", {
        headers: {
          "Authorization": roleConfig.token ? `Bearer ${roleConfig.token}` : "",
          "X-Actor-Role": currentRole,
        },
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }

      const json = await res.json();
      setRecords(json.data || []);
    } catch (err: any) {
      setFetchError(err.message || "Erro de comunicação com o serviço de auditoria");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchRecords();
    }
  }, [isOpen, currentRole]);

  if (!isOpen) return null;

  const handleRecordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!justification.trim()) {
      alert("A justificativa técnica é obrigatória para registrar uma decisão auditável.");
      return;
    }

    setIsSubmitting(true);
    setSubmitMessage(null);

    const payload = {
      action,
      entity_type: entityType,
      entity_id: entityId,
      justification: justification.trim(),
      new_state: {
        status: "reviewed_and_approved",
        reviewer_id: roleConfig.roleName,
        timestamp: new Date().toISOString(),
      },
    };

    try {
      const res = await fetch("/api/v1/admin/audit/decisions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": roleConfig.token ? `Bearer ${roleConfig.token}` : "",
          "X-Actor-Role": currentRole,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setJustification("");
        setShowNewForm(false);
        setSubmitMessage("Decisão registrada com sucesso na trilha imutável!");
        await fetchRecords();
      } else {
        const errJson = await res.json().catch(() => ({}));
        alert(`Erro ao registrar decisão: ${errJson.error || res.statusText}`);
      }
    } catch (err: any) {
      alert(`Falha de conexão com a API de auditoria: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(10, 24, 20, 0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "20px",
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Trilha Imutável de Auditoria de Decisões"
    >
      <div
        style={{
          background: "#ffffff",
          borderRadius: "8px",
          width: "100%",
          maxWidth: "880px",
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 20px 40px rgba(0,0,0,0.25)",
          overflow: "hidden",
        }}
      >
        {/* Cabeçalho */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid #d1dbd6",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: "#f7f9f8",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h2 style={{ margin: 0, fontSize: "18px", color: "var(--ink, #15342d)" }}>
                Trilha Imutável de Auditoria de Decisões
              </h2>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  background: "#def0e5",
                  color: "#1a5e3a",
                  padding: "2px 8px",
                  borderRadius: "4px",
                }}
              >
                Cadeia de Hashes Criptográficos (SHA-256)
              </span>
            </div>
            <p style={{ margin: "4px 0 0 0", fontSize: "12.5px", color: "var(--muted, #52675d)" }}>
              Registro append-only de homologações, pareceres metodológicos e ações de governança.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              fontSize: "22px",
              cursor: "pointer",
              color: "var(--muted, #52675d)",
              padding: "4px 8px",
            }}
            aria-label="Fechar modal"
          >
            ×
          </button>
        </div>

        {/* Mensagem de sucesso */}
        {submitMessage && (
          <div style={{ background: "#eef9f2", borderBottom: "1px solid #c2e5d1", padding: "10px 24px", color: "#166534", fontSize: "13px" }}>
            {submitMessage}
          </div>
        )}

        {/* Conteúdo rolável */}
        <div style={{ padding: "20px 24px", overflowY: "auto", flex: 1 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--ink, #15342d)" }}>
              Eventos Registrados ({records.length})
            </span>
            {canAccessAudit ? (
              <button
                onClick={() => setShowNewForm(!showNewForm)}
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  padding: "6px 12px",
                  borderRadius: "4px",
                  background: showNewForm ? "#e9edea" : "#15342d",
                  color: showNewForm ? "#15342d" : "#ffffff",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                {showNewForm ? "Cancelar" : "+ Homologar Nova Decisão"}
              </button>
            ) : null}
          </div>

          {/* Bloqueio de Acesso Não Autorizado */}
          {!canAccessAudit && (
            <div
              style={{
                background: "#fef3c7",
                border: "1px solid #fde68a",
                borderRadius: "6px",
                padding: "16px",
                color: "#92400e",
                fontSize: "13px",
                lineHeight: "1.5",
              }}
            >
              <strong>Acesso Restrito:</strong> A visualização e inserção na trilha imutável de auditoria exige autenticação com papel de <strong>Revisor</strong> ou <strong>Publicador</strong>. Alterne o seletor de papel no topo da página para autenticar sua sessão.
            </div>
          )}

          {/* Estado de Carregamento */}
          {canAccessAudit && isLoading && (
            <div style={{ padding: "24px 0", textAlign: "center", color: "var(--muted, #52675d)", fontSize: "13px" }}>
              Carregando registros persistidos da trilha de auditoria...
            </div>
          )}

          {/* Estado de Erro / Indisponibilidade */}
          {canAccessAudit && !isLoading && fetchError && (
            <div
              style={{
                background: "#fef2f2",
                border: "1px solid #fee2e2",
                borderRadius: "6px",
                padding: "14px 16px",
                color: "#991b1b",
                fontSize: "13px",
                lineHeight: "1.5",
              }}
            >
              <strong>Trilha Indisponível:</strong> {fetchError}.
              <div style={{ fontSize: "11.5px", marginTop: "4px", color: "#b91c1c" }}>
                Conforme diretrizes de integridade, dados de exemplo não são apresentados como histórico oficial.
              </div>
            </div>
          )}

          {/* Formulário de Nova Decisão */}
          {showNewForm && canAccessAudit && (
            <form
              onSubmit={handleRecordSubmit}
              style={{
                background: "#fbfbfb",
                border: "1px solid #d1dbd6",
                borderRadius: "6px",
                padding: "16px",
                marginBottom: "20px",
              }}
            >
              <h3 style={{ margin: "0 0 12px 0", fontSize: "14px", color: "var(--ink, #15342d)" }}>
                Homologação de Ação de Governança
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: 700, marginBottom: "4px" }}>
                    Ação:
                  </label>
                  <select
                    value={action}
                    onChange={(e) => setAction(e.target.value)}
                    style={{ width: "100%", padding: "6px 8px", fontSize: "12px", borderRadius: "4px", border: "1px solid #cbd5e1" }}
                  >
                    <option value="approve_calibration">Aprovar Calibração Fiscal</option>
                    <option value="resolve_alert">Resolver Alerta Econômico</option>
                    <option value="publish_guidance_target">Ratificar Meta de Guidance</option>
                    <option value="trigger_replay">Autorizar Replay Operacional</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: 700, marginBottom: "4px" }}>
                    ID da Entidade:
                  </label>
                  <input
                    type="text"
                    value={entityId}
                    onChange={(e) => setEntityId(e.target.value)}
                    style={{ width: "100%", padding: "6px 8px", fontSize: "12px", borderRadius: "4px", border: "1px solid #cbd5e1" }}
                    required
                  />
                </div>
              </div>
              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", fontSize: "11px", fontWeight: 700, marginBottom: "4px" }}>
                  Justificativa Técnica Obrigatória:
                </label>
                <textarea
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="Descreva a fundamentação empírica, parâmetros revisados ou razão da homologação..."
                  style={{ width: "100%", height: "65px", padding: "8px", fontSize: "12px", borderRadius: "4px", border: "1px solid #cbd5e1" }}
                  required
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
                <button
                  type="button"
                  onClick={() => setShowNewForm(false)}
                  style={{ padding: "6px 12px", fontSize: "12px", background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: "4px", cursor: "pointer" }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{ padding: "6px 14px", fontSize: "12px", fontWeight: 700, background: "#166534", color: "#ffffff", border: "none", borderRadius: "4px", cursor: "pointer" }}
                >
                  {isSubmitting ? "Gravando..." : "Gravar na Trilha"}
                </button>
              </div>
            </form>
          )}

          {/* Lista de Registros da Trilha */}
          {canAccessAudit && !isLoading && !fetchError && records.length === 0 && (
            <div style={{ padding: "24px 0", textAlign: "center", color: "var(--muted, #52675d)", fontSize: "13px" }}>
              Nenhum evento registrado na trilha de auditoria até o momento.
            </div>
          )}

          {canAccessAudit && !isLoading && !fetchError && records.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {records.map((rec, index) => (
                <div
                  key={rec.id}
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: "6px",
                    padding: "14px 16px",
                    background: index === 0 ? "#ffffff" : "#fcfcfc",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "6px" }}>
                    <div>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--ink, #15342d)", marginRight: "8px" }}>
                        {rec.action}
                      </span>
                      <span
                        style={{
                          fontSize: "10.5px",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          padding: "2px 6px",
                          borderRadius: "3px",
                          background: rec.actor_role === "publisher" ? "#def0e5" : rec.actor_role === "reviewer" ? "#faedd9" : "#e2e8f0",
                          color: rec.actor_role === "publisher" ? "#166534" : rec.actor_role === "reviewer" ? "#9a3412" : "#334155",
                        }}
                      >
                        {rec.actor_role} ({rec.actor_id})
                      </span>
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--muted, #52675d)", fontFamily: "monospace" }}>
                      {new Date(rec.created_at).toLocaleString("pt-BR")}
                    </span>
                  </div>

                  <p style={{ margin: "4px 0 8px 0", fontSize: "12.5px", color: "#334155", lineHeight: "1.5" }}>
                    <strong>Justificativa:</strong> {rec.justification}
                  </p>

                  <div
                    style={{
                      background: "#f8fafc",
                      border: "1px solid #f1f5f9",
                      borderRadius: "4px",
                      padding: "8px 10px",
                      fontSize: "10.5px",
                      fontFamily: "monospace",
                      color: "#64748b",
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: "8px",
                    }}
                  >
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      <strong>Payload Hash:</strong> {rec.payload_hash}
                    </div>
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      <strong>Prev Hash:</strong> {rec.prev_log_hash}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Rodapé */}
        <div
          style={{
            padding: "12px 24px",
            borderTop: "1px solid #d1dbd6",
            background: "#f7f9f8",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: "11px", color: "var(--muted, #52675d)" }}>
            PostgreSQL Append-Only Ledger • Encadeamento Criptográfico SHA-256
          </span>
          <button
            onClick={onClose}
            style={{
              padding: "6px 16px",
              fontSize: "12.5px",
              fontWeight: 600,
              background: "#15342d",
              color: "#ffffff",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
