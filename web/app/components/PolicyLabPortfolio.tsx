"use client";

import React, { useState } from "react";
import { ProposalDetailModal, type PublicProposal } from "./ProposalDetailModal";

interface PolicyLabPortfolioProps {
  initialProposals?: PublicProposal[];
}

const defaultProposals: PublicProposal[] = [
  {
    id: "prop-fiscal-mandatory-spending",
    title: "Revisão e Eficiência do Gasto Obrigatório e Previdenciário",
    policy_axis: "fiscal_quality",
    status: "hypothesis_under_review",
    problem_statement: "O crescimento inercial de despesas obrigatórias e indexações automáticas comprime o espaço para investimentos públicos essenciais e pressiona a sustentabilidade da dívida pública.",
    causal_mechanism: "A desindexação seletiva de benefícios, convergência de regras de aposentadoria e revisão periódica de programas sociais reduzem despesas primárias recorrentes em até 1,2% do PIB ao ano, desacelerando a dinâmica da dívida sem prejudicar o piso de proteção social aos mais vulneráveis.",
    cost_estimate_annual_brl: -45.0,
    cost_pct_gdp: -0.4,
    funding_source: "Revisão e focalização de programas sociais, contenção de reajustes automáticos acima do ganho de produtividade e redução de fraudes cadastrais.",
    institutional_competence: "constitutional_amendment",
    responsible_actors: ["Poder Executivo Federal (Ministério da Fazenda / MPO)", "Congresso Nacional (Câmara dos Deputados e Senado Federal)"],
    counterfactual_summary: "Sem a revisão estrutural, a rigidez orçamentária atinge 95% das despesas primárias da União, paralisando serviços públicos e elevando a dívida bruta para além de 85% do PIB até 2030.",
    empirical_evidence: "Evidências empíricas de consolidações fiscais baseadas em corte de despesas correntes (Alesina & Ardagna, 2013; Relatórios de Acompanhamento Fiscal da IFI/Senado 2024-2026).",
    target_indicator_id: "br.debt.gross_pct_gdp",
  },
  {
    id: "prop-infra-investment-acceleration",
    title: "Aceleração do Investimento em Infraestrutura via Parcerias e Desregulamentação",
    policy_axis: "infrastructure_investment",
    status: "hypothesis_under_review",
    problem_statement: "A taxa de investimento no Brasil (FBCF em torno de 16-17% do PIB) é historicamente insuficiente para sustentar crescimento do PIB potencial acima de 2,5% ao ano.",
    causal_mechanism: "A expansão de garantias federais para debêntures de infraestrutura, desregulamentação ambiental transparente e reforço de segurança jurídica nas concessões elevam a FBCF privada em 1,5 p.p. do PIB em 4 anos, gerando ganhos de produtividade logística e crescimento potencial adicional de 0,5% a.a.",
    cost_estimate_annual_brl: 12.0,
    cost_pct_gdp: 0.1,
    funding_source: "Fundo Garantidor de Infraestrutura (FGI), receitas de outorgas de concessões anteriores e atração de investimento direto no país (IDP).",
    institutional_competence: "ordinary_law",
    responsible_actors: ["Ministério dos Transportes", "Ministério de Portos e Aeroportos", "Agências Reguladoras (ANTT, ANTAQ, ANAC)", "BNDES"],
    counterfactual_summary: "Estagnação do investimento logístico, gargalos de escoamento da safra agrícola, aumento contínuo do custo de frete e perda de competitividade externa.",
    empirical_evidence: "Estudos IPEA/CNI sobre retorno social da infraestrutura e multiplicador de longo prazo do investimento privado (Ferreira & Malliagaros, 1998; Frischtak, 2022).",
    target_indicator_id: "br.investment.gfcf_pct_gdp",
  },
  {
    id: "prop-tax-reform-neutrality",
    title: "Transição Tributária para o IBS/CBS com Neutralidade de Carga e Fim da Cumulatividade",
    policy_axis: "tax_productivity",
    status: "hypothesis_under_review",
    problem_statement: "O sistema de tributação sobre o consumo no Brasil gera o maior contencioso tributário do mundo (mais de 70% do PIB) e severa distorção na alocação de fatores produtivos.",
    causal_mechanism: "A unificação em IVA dual (IBS e CBS) de base ampla com crédito financeiro amplo e neutralidade de carga elimina a cumulatividade de resíduos tributários, desonera investimentos e exportações, e eleva a produtividade total dos fatores (PTF) em até 10% no ciclo decenal.",
    cost_estimate_annual_brl: 0.0,
    cost_pct_gdp: 0.0,
    funding_source: "Compensação de alíquotas com base no modelo de alíquota de referência calculado pelo Comitê Gestor do IBS e Receita Federal do Brasil.",
    institutional_competence: "supplementary_law",
    responsible_actors: ["Congresso Nacional", "Comitê Gestor do IBS", "Secretaria Especial da Receita Federal do Brasil"],
    counterfactual_summary: "Manutenção da guerra fiscal interestadual, insegurança jurídica crônica para novas plantas industriais e desindustrialização precoce.",
    empirical_evidence: "Simulações de equilíbrio geral computável IPEA/UFMG (Appy et al., 2020; Pires, 2023) estimando incremento de 12% a 20% no PIB potencial em 15 anos.",
    target_indicator_id: "br.ipca.12m",
  },
];

const competenceBadges: Record<string, { label: string; color: string; bg: string }> = {
  executive_decree: { label: "Poder Executivo (Decreto)", color: "#1b5e20", bg: "#e8f5e9" },
  ordinary_law: { label: "Congresso (Lei Ordinária)", color: "#0d47a1", bg: "#e3f2fd" },
  supplementary_law: { label: "Congresso (Lei Complementar)", color: "#4a148c", bg: "#f3e5f5" },
  constitutional_amendment: { label: "Congresso (PEC Constitucional)", color: "#b71c1c", bg: "#ffebee" },
};

export function PolicyLabPortfolio({ initialProposals }: PolicyLabPortfolioProps) {
  const proposals = initialProposals && initialProposals.length > 0 ? initialProposals : defaultProposals;
  const [selectedAxis, setSelectedAxis] = useState<string>("all");
  const [activeModalProposal, setActiveModalProposal] = useState<PublicProposal | null>(null);

  const filtered = selectedAxis === "all"
    ? proposals
    : proposals.filter((p) => p.policy_axis === selectedAxis);

  return (
    <section style={{ margin: "48px 0" }}>
      <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2>Policy Lab — Carteira de Propostas Públicas</h2>
          <span style={{ fontSize: "11px", letterSpacing: "1px", color: "var(--muted, #52675d)" }}>
            ANÁLISE DE IMPACTO, FINANCIAMENTO & COMPETÊNCIA CONSTITUCIONAL
          </span>
        </div>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {["all", "fiscal_quality", "infrastructure_investment", "tax_productivity"].map((axis) => {
            const labels: Record<string, string> = {
              all: "Todas as Frentes",
              fiscal_quality: "Fiscal",
              infrastructure_investment: "Infraestrutura",
              tax_productivity: "Tributária",
            };
            const isSelected = selectedAxis === axis;
            return (
              <button
                key={axis}
                type="button"
                onClick={() => setSelectedAxis(axis)}
                style={{
                  background: isSelected ? "var(--ink, #15342d)" : "#fff",
                  color: isSelected ? "#fff" : "var(--muted, #52675d)",
                  border: "1px solid var(--line, #d5dccf)",
                  borderRadius: "20px",
                  padding: "5px 12px",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                {labels[axis] || axis}
              </button>
            );
          })}
        </div>
      </div>

      <p style={{ color: "var(--muted, #52675d)", fontSize: "14px", marginTop: "8px", marginBottom: "24px" }}>
        Carteira demonstradora de 3 propostas canônicas avaliadas com estimativa de custo, mecanismo de transmissão causal,
        fontes orçamentárias de financiamento e delimitação estrita de competências entre o Poder Executivo e o Congresso Nacional.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "24px",
        }}
      >
        {filtered.map((p) => {
          const comp = competenceBadges[p.institutional_competence] || {
            label: p.institutional_competence,
            color: "#333",
            bg: "#eee",
          };
          const costNum = Number(p.cost_estimate_annual_brl);
          const costText = costNum < 0
            ? `Economia de R$ ${Math.abs(costNum).toFixed(1)} bi/ano`
            : costNum === 0
            ? "Neutra (R$ 0,0 bi)"
            : `Investimento de R$ ${costNum.toFixed(1)} bi/ano`;

          return (
            <div
              key={p.id}
              style={{
                background: "#fff",
                border: "1px solid var(--line, #d5dccf)",
                borderRadius: "6px",
                padding: "22px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "6px" }}>
                  <span
                    style={{
                      fontFamily: "monospace",
                      fontSize: "11px",
                      background: "#f0f2ed",
                      padding: "2px 7px",
                      borderRadius: "3px",
                      color: "var(--ink, #15342d)",
                    }}
                  >
                    {p.id}
                  </span>
                  <span
                    style={{
                      fontSize: "11px",
                      background: comp.bg,
                      color: comp.color,
                      fontWeight: 600,
                      padding: "3px 8px",
                      borderRadius: "4px",
                    }}
                  >
                    {comp.label}
                  </span>
                </div>

                <h3 style={{ margin: "0 0 10px 0", fontSize: "16px", color: "var(--ink, #15342d)", lineHeight: 1.4 }}>
                  {p.title}
                </h3>

                <p style={{ margin: "0 0 16px 0", fontSize: "13.5px", color: "var(--muted, #52675d)", lineHeight: 1.5 }}>
                  {p.problem_statement}
                </p>

                <div
                  style={{
                    background: "#f9faf7",
                    border: "1px solid var(--line, #d5dccf)",
                    borderRadius: "4px",
                    padding: "12px 14px",
                    marginBottom: "16px",
                  }}
                >
                  <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "1px", color: "var(--muted, #52675d)" }}>
                    Impacto Fiscal Estimado
                  </div>
                  <div style={{ fontSize: "15px", fontWeight: "bold", color: costNum < 0 ? "#1b5e20" : "var(--ink, #15342d)", marginTop: "2px" }}>
                    {costText}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--muted, #52675d)", marginTop: "6px" }}>
                    <strong>Financiamento:</strong> {p.funding_source}
                  </div>
                </div>
              </div>

              <div>
                <button
                  type="button"
                  onClick={() => setActiveModalProposal(p)}
                  style={{
                    width: "100%",
                    background: "#f0f2ed",
                    color: "var(--ink, #15342d)",
                    border: "1px solid var(--line, #d5dccf)",
                    borderRadius: "4px",
                    padding: "8px 14px",
                    fontSize: "12.5px",
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#e4e8df")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "#f0f2ed")}
                >
                  Ver Detalhes e Mecanismo Causal &rarr;
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <ProposalDetailModal
        proposal={activeModalProposal}
        isOpen={activeModalProposal !== null}
        onClose={() => setActiveModalProposal(null)}
      />
    </section>
  );
}
