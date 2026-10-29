"use client";

import React, { useState } from "react";

interface OperationalReplayModalProps {
  isOpen: boolean;
  onClose: () => void;
  onReplayDispatched?: () => void;
}

export function OperationalReplayModal({
  isOpen,
  onClose,
  onReplayDispatched,
}: OperationalReplayModalProps) {
  const [reason, setReason] = useState("");
  const [indicatorId, setIndicatorId] = useState("");
  const [eventType, setEventType] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    message: string;
    replayId?: string;
    count?: number;
  } | null>(null);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!reason.trim()) {
      setResult({
        success: false,
        message: "A justificativa operacional é obrigatória para fins de auditoria.",
      });
      return;
    }

    setIsSubmitting(true);
    setResult(null);

    try {
      const res = await fetch("/api/v1/admin/outbox/replay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason: reason.trim(),
          triggered_by: "painel-web-admin",
          filter_indicator_id: indicatorId || undefined,
          filter_event_type: eventType || undefined,
        }),
      });

      const json = await res.json();
      if (!res.ok) {
        setResult({
          success: false,
          message: json.error || "Erro ao acionar replay operacional.",
        });
      } else {
        setResult({
          success: true,
          message: "Replay operacional disparado com sucesso.",
          replayId: json.data?.replay_id,
          count: json.data?.events_replayed_count,
        });
        if (onReplayDispatched) {
          onReplayDispatched();
        }
      }
    } catch (err: unknown) {
      setResult({
        success: false,
        message: err instanceof Error ? err.message : "Erro inesperado de rede.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        background: "rgba(21, 52, 45, 0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "20px",
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="replay-modal-title"
    >
      <div
        style={{
          background: "#fff",
          maxWidth: "560px",
          width: "100%",
          borderRadius: "8px",
          padding: "28px",
          border: "1px solid var(--line, #d5dccf)",
          boxShadow: "0 20px 40px rgba(0,0,0,0.15)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "16px",
          }}
        >
          <h3 id="replay-modal-title" style={{ margin: 0, fontSize: "20px", color: "var(--ink, #15342d)" }}>
            Replay Operacional de Eventos
          </h3>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              fontSize: "24px",
              cursor: "pointer",
              color: "var(--muted, #52675d)",
            }}
            aria-label="Fechar modal"
          >
            &times;
          </button>
        </div>

        <p style={{ fontSize: "14px", color: "var(--muted, #52675d)", marginBottom: "20px" }}>
          O reprocessamento reinicia os eventos da outbox para estado <code>pending</code>.
          Todas as ações de replay geram um registro imutável em <code>outbox_replay_audit</code>.
        </p>

        {result && (
          <div
            style={{
              padding: "12px 16px",
              borderRadius: "4px",
              marginBottom: "16px",
              fontSize: "14px",
              background: result.success ? "#e8f5e9" : "#ffebee",
              borderLeft: `4px solid ${result.success ? "#216044" : "#c62828"}`,
              color: result.success ? "#1b5e20" : "#b71c1c",
            }}
          >
            <div>{result.message}</div>
            {result.replayId && (
              <small style={{ display: "block", marginTop: "4px" }}>
                ID: <code>{result.replayId}</code> | Eventos redefinidos: {result.count}
              </small>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "16px" }}>
            <label
              htmlFor="replay-reason"
              style={{ display: "block", fontSize: "13px", fontWeight: "bold", marginBottom: "6px" }}
            >
              Justificativa Obrigatória *
            </label>
            <textarea
              id="replay-reason"
              rows={3}
              required
              placeholder="Ex: Reprocessamento após ajuste no conector de dados ou validação de vintage..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              style={{
                width: "100%",
                padding: "10px",
                borderRadius: "4px",
                border: "1px solid var(--line, #d5dccf)",
                fontSize: "14px",
                fontFamily: "inherit",
              }}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "20px" }}>
            <div>
              <label
                htmlFor="filter-indicator"
                style={{ display: "block", fontSize: "13px", fontWeight: "bold", marginBottom: "6px" }}
              >
                Filtrar Indicador
              </label>
              <select
                id="filter-indicator"
                value={indicatorId}
                onChange={(e) => setIndicatorId(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px",
                  borderRadius: "4px",
                  border: "1px solid var(--line, #d5dccf)",
                  fontSize: "13px",
                  background: "#fff",
                }}
              >
                <option value="">Todos os indicadores</option>
                <option value="br.ipca.monthly">IPCA mensal (IBGE)</option>
                <option value="br.selic.daily">Selic diária (BCB)</option>
                <option value="br.debt.gross_pct_gdp">Dívida bruta (BCB)</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="filter-event-type"
                style={{ display: "block", fontSize: "13px", fontWeight: "bold", marginBottom: "6px" }}
              >
                Filtrar Tipo de Evento
              </label>
              <select
                id="filter-event-type"
                value={eventType}
                onChange={(e) => setEventType(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px",
                  borderRadius: "4px",
                  border: "1px solid var(--line, #d5dccf)",
                  fontSize: "13px",
                  background: "#fff",
                }}
              >
                <option value="">Todos os eventos</option>
                <option value="EconomicIndicatorUpdated">EconomicIndicatorUpdated</option>
                <option value="HistoricalSeriesRevised">HistoricalSeriesRevised</option>
                <option value="DataQualityFailed">DataQualityFailed</option>
                <option value="DynamicSimulationRequested">DynamicSimulationRequested</option>
              </select>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              style={{
                padding: "8px 16px",
                borderRadius: "4px",
                border: "1px solid var(--line, #d5dccf)",
                background: "#fff",
                cursor: "pointer",
                fontSize: "13px",
              }}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !reason.trim()}
              style={{
                padding: "8px 20px",
                borderRadius: "4px",
                border: "none",
                background: isSubmitting || !reason.trim() ? "#ccc" : "var(--green, #216044)",
                color: "#fff",
                fontWeight: "bold",
                cursor: isSubmitting || !reason.trim() ? "not-allowed" : "pointer",
                fontSize: "13px",
              }}
            >
              {isSubmitting ? "Processando..." : "Confirmar e Disparar Replay"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
