"use client";

import React, { useEffect } from "react";

export interface PublicProposal {
  id: string;
  title: string;
  policy_axis: string;
  status: string;
  problem_statement: string;
  causal_mechanism: string;
  cost_estimate_annual_brl: number | string;
  cost_pct_gdp?: number | string | null;
  funding_source: string;
  institutional_competence: string;
  responsible_actors: string[];
  counterfactual_summary: string;
  empirical_evidence: string;
  target_indicator_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

interface ProposalDetailModalProps {
  proposal: PublicProposal | null;
  isOpen: boolean;
  onClose: () => void;
}

const competenceLabels: Record<string, { label: string; color: string; bg: string }> = {
  executive_decree: { label: "Poder Executivo (Decreto / Portaria)", color: "#1b5e20", bg: "#e8f5e9" },
  ordinary_law: { label: "Congresso Nacional (Lei Ordinária)", color: "#0d47a1", bg: "#e3f2fd" },
  supplementary_law: { label: "Congresso Nacional (Lei Complementar)", color: "#4a148c", bg: "#f3e5f5" },
  constitutional_amendment: { label: "Congresso Nacional (Emenda Constitucional - PEC)", color: "#b71c1c", bg: "#ffebee" },
};

const axisLabels: Record<string, string> = {
  fiscal_quality: "Qualidade do Gasto e Sustentabilidade Fiscal",
  infrastructure_investment: "Investimento em Infraestrutura & Logística",
  tax_productivity: "Reforma Tributária & Produtividade",
  human_capital: "Educação & Capital Humano",
  state_efficiency: "Eficiência de Gestão & Serviços Públicos",
};

export function ProposalDetailModal({ proposal, isOpen, onClose }: ProposalDetailModalProps) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !proposal) return null;

  const compInfo = competenceLabels[proposal.institutional_competence] || {
    label: proposal.institutional_competence,
    color: "#333",
    bg: "#eee",
  };

  const costNum = Number(proposal.cost_estimate_annual_brl);
  const costFormatted = costNum < 0
    ? `Economia líquida de R$ ${Math.abs(costNum).toFixed(1)} bi/ano`
    : costNum === 0
    ? "Neutra (Impacto fiscal 0,00)"
    : `Investimento de R$ ${costNum.toFixed(1)} bi/ano`;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        backgroundColor: "rgba(21, 52, 45, 0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "16px",
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-proposal-title"
    >
      <div
        style={{
          background: "#fff",
          borderRadius: "8px",
          width: "100%",
          maxWidth: "840px",
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
          border: "1px solid var(--line, #d5dccf)",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "24px 28px",
            borderBottom: "1px solid var(--line, #d5dccf)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            background: "#fafaf7",
          }}
        >
          <div>
            <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "8px", flexWrap: "wrap" }}>
              <span
                style={{
                  fontFamily: "monospace",
                  fontSize: "11px",
                  background: "#e8ede6",
                  color: "var(--ink, #15342d)",
                  padding: "3px 8px",
                  borderRadius: "4px",
                }}
              >
                {proposal.id}
              </span>
              <span
                style={{
                  fontSize: "11px",
                  background: compInfo.bg,
                  color: compInfo.color,
                  fontWeight: 600,
                  padding: "3px 8px",
                  borderRadius: "4px",
                }}
              >
                {compInfo.label}
              </span>
              <span
                style={{
                  fontSize: "11px",
                  background: "#fff8e1",
                  color: "#f57f17",
                  border: "1px solid #ffe082",
                  padding: "2px 7px",
                  borderRadius: "4px",
                }}
              >
                Hipótese sob Avaliação
              </span>
            </div>
            <h2 id="modal-proposal-title" style={{ margin: "4px 0", fontSize: "20px", color: "var(--ink, #15342d)" }}>
              {proposal.title}
            </h2>
            <div style={{ fontSize: "13px", color: "var(--muted, #52675d)", marginTop: "2px" }}>
              Eixo: {axisLabels[proposal.policy_axis] || proposal.policy_axis}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              fontSize: "24px",
              lineHeight: 1,
              color: "var(--muted, #52675d)",
              cursor: "pointer",
              padding: "4px 8px",
            }}
            aria-label="Fechar modal de proposta"
          >
            &times;
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: "28px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "22px" }}>
          {/* Diagnóstico */}
          <div>
            <h3 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "1px", color: "var(--muted, #52675d)", margin: "0 0 6px 0" }}>
              1. Diagnóstico e Problema a Resolver
            </h3>
            <p style={{ margin: 0, fontSize: "14.5px", lineHeight: 1.6, color: "var(--ink, #15342d)" }}>
              {proposal.problem_statement}
            </p>
          </div>

          {/* Mecanismo Causal */}
          <div style={{ background: "#f8f9f6", padding: "16px 20px", borderRadius: "6px", border: "1px solid var(--line, #d5dccf)" }}>
            <h3 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "1px", color: "var(--green, #216044)", margin: "0 0 6px 0" }}>
              2. Hipótese Causal & Transmissão Econômica
            </h3>
            <p style={{ margin: 0, fontSize: "14px", lineHeight: 1.6, color: "var(--ink, #15342d)" }}>
              {proposal.causal_mechanism}
            </p>
          </div>

          {/* Custo & Financiamento */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div style={{ border: "1px solid var(--line, #d5dccf)", padding: "14px 18px", borderRadius: "6px" }}>
              <div style={{ fontSize: "11px", letterSpacing: "1px", textTransform: "uppercase", color: "var(--muted, #52675d)" }}>
                Custo / Impacto Anual
              </div>
              <div style={{ fontSize: "16px", fontWeight: "bold", color: costNum < 0 ? "#1b5e20" : "var(--ink, #15342d)", marginTop: "4px" }}>
                {costFormatted}
              </div>
              {proposal.cost_pct_gdp && (
                <div style={{ fontSize: "12px", color: "var(--muted, #52675d)", marginTop: "2px" }}>
                  Aproximadamente {proposal.cost_pct_gdp}% do PIB
                </div>
              )}
            </div>
            <div style={{ border: "1px solid var(--line, #d5dccf)", padding: "14px 18px", borderRadius: "6px" }}>
              <div style={{ fontSize: "11px", letterSpacing: "1px", textTransform: "uppercase", color: "var(--muted, #52675d)" }}>
                Fonte de Financiamento / Compensação
              </div>
              <div style={{ fontSize: "13px", color: "var(--ink, #15342d)", marginTop: "4px", lineHeight: 1.4 }}>
                {proposal.funding_source}
              </div>
            </div>
          </div>

          {/* Atores Responsáveis */}
          <div>
            <h3 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "1px", color: "var(--muted, #52675d)", margin: "0 0 6px 0" }}>
              3. Atores Institucionais Envolvidos
            </h3>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {proposal.responsible_actors.map((actor, idx) => (
                <span
                  key={idx}
                  style={{
                    background: "#e8ede6",
                    color: "var(--ink, #15342d)",
                    padding: "4px 10px",
                    borderRadius: "4px",
                    fontSize: "12.5px",
                  }}
                >
                  {actor}
                </span>
              ))}
            </div>
          </div>

          {/* Cenário Contrafactual */}
          <div>
            <h3 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "1px", color: "var(--muted, #52675d)", margin: "0 0 6px 0" }}>
              4. Cenário Contrafactual (Caso a Medida Não Ocorra)
            </h3>
            <p style={{ margin: 0, fontSize: "14px", lineHeight: 1.6, color: "var(--ink, #15342d)" }}>
              {proposal.counterfactual_summary}
            </p>
          </div>

          {/* Evidências Empíricas */}
          <div>
            <h3 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "1px", color: "var(--muted, #52675d)", margin: "0 0 6px 0" }}>
              5. Evidências Empíricas & Referências
            </h3>
            <div
              style={{
                background: "#fafaf7",
                padding: "12px 16px",
                borderRadius: "4px",
                borderLeft: "3px solid var(--green, #216044)",
                fontSize: "13px",
                color: "var(--muted, #52675d)",
                lineHeight: 1.5,
              }}
            >
              {proposal.empirical_evidence}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "16px 28px",
            borderTop: "1px solid var(--line, #d5dccf)",
            background: "#fafaf7",
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "var(--ink, #15342d)",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              padding: "8px 20px",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Fechar Detalhes
          </button>
        </div>
      </div>
    </div>
  );
}
