"use client";

import React from "react";

export interface GuidanceCommitment {
  id: string;
  proposal_id?: string | null;
  proposal_title?: string | null;
  indicator_id: string;
  name: string;
  horizon_year: number;
  status: string;
  baseline_period: string;
  baseline_value: number | string;
  target_value: number | string;
  forecast_value?: number | string | null;
  actual_latest_value?: number | string | null;
  actual_reference_period?: string | null;
  actual_quality_status?: string | null;
  unit: string;
  variance_explanation?: string | null;
  review_policy: string;
  human_review_required: boolean;
  created_at?: string;
}

interface GuidanceCommitmentsMatrixProps {
  initialCommitments?: GuidanceCommitment[];
}

const defaultCommitments: GuidanceCommitment[] = [
  {
    id: "comm-debt-stabilization-2030",
    proposal_id: "prop-fiscal-mandatory-spending",
    proposal_title: "Revisão e Eficiência do Gasto Obrigatório e Previdenciário",
    indicator_id: "br.debt.gross_pct_gdp",
    name: "Estabilização da Dívida Bruta do Governo Geral até 2030",
    horizon_year: 2030,
    status: "experimental_hypothesis",
    baseline_period: "2025-12",
    baseline_value: 77.8,
    target_value: 75.0,
    forecast_value: 81.4,
    actual_latest_value: null,
    actual_reference_period: null,
    actual_quality_status: null,
    unit: "% do PIB",
    variance_explanation: "Divergência entre o cenário de continuidade (dívida em alta devido a juros reais elevados) e a meta experimental de estabilização fundamentada nas propostas do Policy Lab.",
    review_policy: "annual",
    human_review_required: true,
  },
  {
    id: "comm-inflation-convergence-2030",
    proposal_id: "prop-tax-reform-neutrality",
    proposal_title: "Transição Tributária para o IBS/CBS com Neutralidade de Carga",
    indicator_id: "br.ipca.12m",
    name: "Convergência da Inflação Anual (IPCA 12m) ao Centro da Meta",
    horizon_year: 2030,
    status: "experimental_hypothesis",
    baseline_period: "2025-12",
    baseline_value: 4.1,
    target_value: 3.0,
    forecast_value: 3.8,
    actual_latest_value: null,
    actual_reference_period: null,
    actual_quality_status: null,
    unit: "% a.a.",
    variance_explanation: "Meta contínua de 3,00% com intervalo de tolerância de 1,50 p.p. fixada pelo CMN para o IPCA acumulado em 12 meses; modelo projeta pressão residual no curto prazo.",
    review_policy: "annual",
    human_review_required: true,
  },
  {
    id: "comm-investment-rate-2030",
    proposal_id: "prop-infra-investment-acceleration",
    proposal_title: "Aceleração do Investimento em Infraestrutura via Parcerias",
    indicator_id: "br.investment.gfcf_pct_gdp",
    name: "Elevação da Taxa de Investimento (FBCF) para 20% do PIB",
    horizon_year: 2030,
    status: "experimental_hypothesis",
    baseline_period: "2025-12",
    baseline_value: 16.5,
    target_value: 20.0,
    forecast_value: 17.2,
    actual_latest_value: null,
    actual_reference_period: null,
    actual_quality_status: null,
    unit: "% do PIB",
    variance_explanation: "Meta experimental condicionada à segurança jurídica de concessões e atração de capital privado de longo prazo.",
    review_policy: "annual",
    human_review_required: true,
  },
];

export function GuidanceCommitmentsMatrix({ initialCommitments }: GuidanceCommitmentsMatrixProps) {
  const commitments = initialCommitments && initialCommitments.length > 0 ? initialCommitments : defaultCommitments;

  return (
    <section style={{ margin: "48px 0" }}>
      <div className="section-title">
        <div>
          <h2>Guidance Brasil — 2027–2030 (Compromissos Plurianuais)</h2>
          <span style={{ fontSize: "11px", letterSpacing: "1px", color: "var(--muted, #52675d)" }}>
            MATRIZ DE 4 QUADRANTES: BASELINE &bull; TARGET &bull; FORECAST &bull; ACTUAL
          </span>
        </div>
      </div>

      <p style={{ color: "var(--muted, #52675d)", fontSize: "14px", marginTop: "8px", marginBottom: "20px" }}>
        Separação metodológica rigorosa entre o ponto de partida ilustrativo (baseline experimental), a meta proposta para o mandato,
        a projeção do modelo econômico e as observações apuradas. Atualizações de séries nunca apagam metas nem omitem desvios.
      </p>

      <div
        style={{
          background: "#fff",
          border: "1px solid var(--line, #d5dccf)",
          borderRadius: "6px",
          overflowX: "auto",
          boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13.5px", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "#f8f9f6", borderBottom: "1px solid var(--line, #d5dccf)", color: "var(--muted, #52675d)" }}>
              <th style={{ padding: "14px 16px", fontWeight: 600 }}>Compromisso / Indicador</th>
              <th style={{ padding: "14px 16px", fontWeight: 600 }}>Horizonte</th>
              <th style={{ padding: "14px 16px", fontWeight: 600 }}>Baseline (Ilustrativa)</th>
              <th style={{ padding: "14px 16px", fontWeight: 600 }}>Meta Proposta</th>
              <th style={{ padding: "14px 16px", fontWeight: 600 }}>Projeção (Forecast)</th>
              <th style={{ padding: "14px 16px", fontWeight: 600 }}>Observação Recente (Actual)</th>
              <th style={{ padding: "14px 16px", fontWeight: 600 }}>Desvio (Obs - Meta)</th>
              <th style={{ padding: "14px 16px", fontWeight: 600 }}>Governança</th>
            </tr>
          </thead>
          <tbody>
            {commitments.map((c) => {
              const bVal = Number(c.baseline_value);
              const tVal = Number(c.target_value);
              const fVal = c.forecast_value !== null && c.forecast_value !== undefined ? Number(c.forecast_value) : null;
              const aVal = c.actual_latest_value !== null && c.actual_latest_value !== undefined ? Number(c.actual_latest_value) : null;

              const delta = aVal !== null ? aVal - tVal : null;
              const deltaFormatted = delta !== null
                ? `${delta > 0 ? "+" : ""}${delta.toFixed(2)} p.p.`
                : "Aguardando";

              return (
                <tr
                  key={c.id}
                  style={{
                    borderBottom: "1px solid var(--line, #d5dccf)",
                    transition: "background 0.1s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#fafaf7")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <td style={{ padding: "14px 16px", verticalAlign: "top" }}>
                    <div style={{ fontWeight: 600, color: "var(--ink, #15342d)" }}>{c.name}</div>
                    <div style={{ fontFamily: "monospace", fontSize: "11px", color: "var(--muted, #52675d)", marginTop: "2px" }}>
                      {c.indicator_id}
                    </div>
                    {c.proposal_title && (
                      <div style={{ fontSize: "11.5px", color: "var(--green, #216044)", marginTop: "4px" }}>
                        Vínculo: {c.proposal_title}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: "14px 16px", verticalAlign: "top", fontWeight: 500 }}>
                    {c.horizon_year}
                  </td>
                  <td style={{ padding: "14px 16px", verticalAlign: "top" }}>
                    <div style={{ fontWeight: 600 }}>{bVal.toFixed(1)} {c.unit}</div>
                    <div style={{ fontSize: "11px", color: "var(--muted, #52675d)" }}>ref: {c.baseline_period}</div>
                    <span
                      style={{
                        display: "inline-block",
                        marginTop: "4px",
                        fontSize: "10px",
                        background: "#f0f4f1",
                        color: "#52675d",
                        border: "1px solid #d5dccf",
                        padding: "1px 6px",
                        borderRadius: "3px",
                      }}
                    >
                      Ilustrativa
                    </span>
                  </td>
                  <td style={{ padding: "14px 16px", verticalAlign: "top" }}>
                    <div style={{ fontWeight: 700, color: "var(--green, #216044)" }}>
                      {tVal.toFixed(1)} {c.unit}
                    </div>
                    <span
                      style={{
                        display: "inline-block",
                        marginTop: "4px",
                        fontSize: "10px",
                        background: "#fff8e1",
                        color: "#f57f17",
                        border: "1px solid #ffe082",
                        padding: "1px 6px",
                        borderRadius: "3px",
                      }}
                    >
                      Hipotética
                    </span>
                  </td>
                  <td style={{ padding: "14px 16px", verticalAlign: "top" }}>
                    {fVal !== null ? (
                      <div>
                        <div style={{ fontWeight: 600 }}>{fVal.toFixed(1)} {c.unit}</div>
                        <div style={{ fontSize: "11px", color: "var(--muted, #52675d)" }}>Cenário Base</div>
                      </div>
                    ) : (
                      <span style={{ color: "var(--muted, #52675d)" }}>—</span>
                    )}
                  </td>
                  <td style={{ padding: "14px 16px", verticalAlign: "top" }}>
                    {aVal !== null ? (
                      <div>
                        <div style={{ fontWeight: 700, color: "var(--ink, #15342d)" }}>
                          {aVal.toFixed(1)} {c.unit}
                        </div>
                        <div
                          style={{
                            fontSize: "11px",
                            color:
                              c.actual_quality_status === "provisional"
                                ? "#1b5e20"
                                : c.actual_quality_status === "verified"
                                ? "#0d47a1"
                                : "var(--muted, #52675d)",
                          }}
                        >
                          {c.actual_quality_status === "provisional"
                            ? `Captura provisória da origem (${c.actual_reference_period ?? "período recente"})`
                            : c.actual_quality_status === "verified"
                            ? `Oficial auditado (${c.actual_reference_period ?? "período recente"})`
                            : `Demonstração sintética (${c.actual_reference_period ?? "fixture"})`}
                        </div>
                      </div>
                    ) : (
                      <div>
                        <span style={{ color: "var(--muted, #52675d)", fontStyle: "italic", fontSize: "12.5px" }}>
                          Aguardando observação verificada
                        </span>
                        <div style={{ fontSize: "10.5px", color: "var(--muted, #52675d)", marginTop: "2px" }}>
                          Sem captura da série vinculada
                        </div>
                      </div>
                    )}
                  </td>
                  <td style={{ padding: "14px 16px", verticalAlign: "top" }}>
                    <span
                      style={{
                        fontWeight: 600,
                        color: delta === null ? "var(--muted, #52675d)" : Math.abs(delta) < 0.5 ? "#1b5e20" : "#b71c1c",
                      }}
                    >
                      {deltaFormatted}
                    </span>
                  </td>
                  <td style={{ padding: "14px 16px", verticalAlign: "top" }}>
                    <span
                      style={{
                        fontSize: "11px",
                        background: "#f0f2ed",
                        color: "var(--ink, #15342d)",
                        padding: "2px 6px",
                        borderRadius: "3px",
                        display: "inline-block",
                        whiteSpace: "nowrap",
                      }}
                    >
                      Parecer Humano Req.
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
