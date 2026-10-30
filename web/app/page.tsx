import { DynamicSimulationSection } from "./components/DynamicSimulationSection";
import { InstitutionalMatrix, type InstitutionalActor } from "./components/InstitutionalMatrix";
import { SourceFreshnessPanel, type SourceSchedule } from "./components/SourceFreshnessPanel";
import { GovernanceDisclaimerAlert } from "./components/GovernanceDisclaimerAlert";
import { PolicyLabPortfolio } from "./components/PolicyLabPortfolio";
import { type PublicProposal } from "./components/ProposalDetailModal";
import { GuidanceCommitmentsMatrix, type GuidanceCommitment } from "./components/GuidanceCommitmentsMatrix";
import { GovernanceAndObservabilitySection } from "./components/GovernanceAndObservabilitySection";
import { type ObservabilityData } from "./components/ObservabilityPlanesPanel";
import { MacroTrajectoryPanel, type TrajectoryPoint } from "./components/MacroTrajectoryPanel";

export const dynamic = "force-dynamic";
type Observation = {
  indicator_id: string;
  reference_period: string;
  value: number;
  unit: string;
  vintage_id: string;
  known_at: string;
  quality_status: string;
  source_uri: string;
  raw_hash: string;
};
type Scenario = {
  id: string;
  scenario_id: string;
  outputs: { horizon_years: number; debt_pct_gdp: string }[];
  inputs: { reference_period: string; assumptions: Record<string, string> };
};
type Alert = {
  id: string;
  severity: string;
  review_status: string;
  evidence: { delta_pp: string };
};
type Catalog = {
  domains: { id: number; name: string; coverage: string }[];
  indicators: {
    indicator_id: string;
    name: string;
    unit: string;
    frequency: string;
  }[];
};
async function load<T>(
  path: string,
  mode: string,
): Promise<{ data: T } | null> {
  try {
    const response = await fetch(
      `${process.env.API_URL || "http://127.0.0.1:18080"}/v1/${path}?mode=${mode}`,
      { cache: "no-store", signal: AbortSignal.timeout(5000) },
    );
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}
const units: Record<string, string> = {
  percent_month: "% no mês",
  percent_year: "% ao ano",
  percent_day: "% ao dia",
  percent_gdp: "% do PIB",
  percent_yoy: "% a.a. (interanual)",
  brl_per_usd: "R$ / US$",
  percent: "%",
};
const assumptionLabels: Record<string, string> = {
  interest: "Juros nominais efetivos ao ano",
  growth: "Crescimento nominal ao ano",
  primary: "Superávit primário / PIB",
  adjustment: "Ajuste estoque-fluxo / PIB",
};
const fmt = (value: number) =>
  new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(value);

const fallbackInstitutions: InstitutionalActor[] = [
  {
    actor_id: "EXEC",
    name: "Poder Executivo Federal",
    sphere: "federal",
    legal_framework: "Art. 84 e 165 da CF/88",
    description: "Formulação e execução de políticas públicas, gestão orçamentária e administração financeira da União.",
  },
  {
    actor_id: "LEG",
    name: "Poder Legislativo (Congresso Nacional)",
    sphere: "federal",
    legal_framework: "Art. 48, 49 e 166 da CF/88",
    description: "Aprovação de leis orçamentárias (PPA, LDO, LOA), reformas tributárias e fiscalização financeira.",
  },
  {
    actor_id: "JUD",
    name: "Poder Judiciário",
    sphere: "federal",
    legal_framework: "Art. 92 e 100 da CF/88",
    description: "Controle jurisdicional e de constitucionalidade das normas fiscais e ordenação de precatórios.",
  },
  {
    actor_id: "BCB",
    name: "Banco Central do Brasil",
    sphere: "independent",
    legal_framework: "Lei Complementar nº 179/2021",
    description: "Execução da política monetária, controle da inflação conforme meta, regulação financeira e estabilidade cambial.",
  },
  {
    actor_id: "TCU",
    name: "Tribunal de Contas da União",
    sphere: "independent",
    legal_framework: "Art. 70 a 73 da CF/88",
    description: "Controle externo e fiscalização contábil, financeira, orçamentária, operacional e patrimonial da União.",
  },
  {
    actor_id: "SUB",
    name: "Entes Subnacionais (Estados e Municípios)",
    sphere: "subnational",
    legal_framework: "Art. 18, 157-159 da CF/88 e LRF (LC 101/2000)",
    description: "Execução descentralizada de serviços essenciais e cumprimento de metas e limites fiscais federativos.",
  },
  {
    actor_id: "SOC",
    name: "Sociedade Civil e Setor Produtivo",
    sphere: "civil_society",
    legal_framework: "Art. 1º, parágrafo único da CF/88",
    description: "Participação social, debate público, produção econômica e destinatária final das políticas públicas.",
  },
];

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ mode?: string }>;
}) {
  const mode = (await searchParams).mode === "fixture" ? "fixture" : "source";
  const [catalog, observations, scenarios, alerts, institutions, sourcesHealth, proposals, guidance, observability, trajectories] = await Promise.all([
    load<Catalog>("indicators", mode),
    load<Observation[]>("observations", mode),
    load<Scenario[]>("scenarios", mode),
    load<Alert[]>("alerts", mode),
    load<InstitutionalActor[]>("institutions", mode),
    load<SourceSchedule[]>("health/sources", mode),
    load<PublicProposal[]>("proposals", mode),
    load<GuidanceCommitment[]>("guidance/commitments", mode),
    load<ObservabilityData>("observability/metrics", mode),
    load<TrajectoryPoint[]>("trajectories", mode),
  ]);
  const latest = new Map<string, Observation>();
  for (const item of observations?.data || []) {
    if (
      !latest.has(item.indicator_id) ||
      latest.get(item.indicator_id)!.reference_period < item.reference_period
    )
      latest.set(item.indicator_id, item);
  }
  const debtObs = latest.get("br.debt.gross_pct_gdp");
  const baseDebtValue = debtObs ? Number(debtObs.value) : 78.5;
  return (
    <main>
      <header>
        <a className="brand" href="/">
          BR<span>F</span> <small>BRASIL DO FUTURO</small>
        </a>
        <span className="pill">FUNDAÇÃO · V0.1</span>
      </header>
      <section className="intro">
        <div className="eyebrow">OBSERVATÓRIO ECONÔMICO NACIONAL</div>
        <h1>
          Entender o presente.
          <br />
          <em>Construir o futuro.</em>
        </h1>
        <p>
          Dados com origem. Cenários com premissas. Decisões com
          responsabilidade.
        </p>
      </section>
      <nav aria-label="Modo dos dados">
        <a
          aria-current={mode === "source" ? "page" : undefined}
          href="/?mode=source"
        >
          Capturas de fontes
        </a>
        <a
          aria-current={mode === "fixture" ? "page" : undefined}
          href="/?mode=fixture"
        >
          Demonstração sintética
        </a>
      </nav>
      <aside className="notice">
        <strong>
          {mode === "fixture"
            ? "DADOS SINTÉTICOS — apenas demonstração técnica"
            : "BASELINE AINDA NÃO VALIDADO"}
        </strong>
        <p>
          {mode === "fixture"
            ? "Valores inventados para testar revisões e rastreabilidade. Não representam a economia brasileira."
            : "Capturas técnicas são provisórias. Licenças, calendários e metadados aguardam validação. A atualidade na origem não foi confirmada."}
        </p>
      </aside>
      <GovernanceDisclaimerAlert />
      {(!catalog || !observations || !scenarios || !alerts) && (
        <p role="alert" className="notice">
          Um ou mais serviços estão indisponíveis. Os dados ausentes não serão
          substituídos por valores de exemplo.
        </p>
      )}
      <section aria-labelledby="indicators">
        <div className="section-title">
          <h2 id="indicators">Pulso econômico</h2>
          <span>{catalog?.data.indicators.length || 6} séries no núcleo P0 / 12 domínios</span>
        </div>
        <div className="cards">
          {catalog?.data.indicators.map((indicator) => {
            const item = latest.get(indicator.indicator_id);
            return (
              <article key={indicator.indicator_id}>
                <span className="eyebrow">
                  {indicator.frequency === "daily"
                    ? "DIÁRIO"
                    : indicator.frequency === "quarterly"
                    ? "TRIMESTRAL"
                    : "MENSAL"}
                </span>
                <h3>{indicator.name}</h3>
                <div className="value">
                  {item
                    ? new Intl.NumberFormat("pt-BR", {
                        maximumFractionDigits:
                          indicator.indicator_id === "br.fx.usd_brl.ptax"
                            ? 4
                            : indicator.frequency === "daily"
                            ? 6
                            : 2,
                      }).format(item.value)
                    : "—"}
                </div>
                <p>{units[indicator.unit] || indicator.unit}</p>
                <p>
                  {item
                    ? `Referência: ${item.reference_period}`
                    : "Nenhuma captura disponível"}
                </p>
                <span className="tag">
                  {item
                    ? mode === "fixture"
                      ? "Sintético"
                      : "Provisório"
                    : "Indisponível"}
                </span>
                {item && (
                  <details>
                    <summary>Ver proveniência</summary>
                    <p>Conhecido em: {item.known_at}</p>
                    <p>
                      Vintage: <code>{item.vintage_id}</code>
                    </p>
                    <p>
                      SHA-256: <code>{item.raw_hash}</code>
                    </p>
                    <p>Origem: {item.source_uri}</p>
                  </details>
                )}
              </article>
            );
          })}
        </div>
      </section>
      <section aria-labelledby="scenarios">
        <div className="section-title">
          <h2 id="scenarios">Cenários condicionais</h2>
          <span>HIPÓTESES · NÃO SÃO PREVISÕES</span>
        </div>
        <p>
          Identidade fiscal simplificada, sem calibração. Juros efetivos,
          crescimento e resultado primário são premissas ilustrativas; não são
          inferidos da Selic diária.
        </p>
        {scenarios?.data.length ? (
          <div className="table-wrap">
            <table>
              <caption>
                Dívida/PIB (%) por horizonte relativo ao período-base
              </caption>
              <thead>
                <tr>
                  <th scope="col">Cenário</th>
                  <th scope="col">Base</th>
                  {[1, 2, 3, 4].map((y) => (
                    <th scope="col" key={y}>
                      +{y} ano{y > 1 ? "s" : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {scenarios.data.map((s) => (
                  <tr key={s.id}>
                    <th scope="row">
                      {
                        (
                          {
                            continuity: "Continuidade",
                            alternative: "Alternativo",
                            adverse: "Adverso",
                          } as Record<string, string>
                        )[s.scenario_id]
                      }
                      <details>
                        <summary>Premissas</summary>
                        <ul>
                          {Object.entries(s.inputs.assumptions).map(
                            ([key, value]) => (
                              <li key={key}>
                                {assumptionLabels[key] || key}:{" "}
                                {fmt(Number(value) * 100)}%
                              </li>
                            ),
                          )}
                        </ul>
                      </details>
                    </th>
                    <td>{s.inputs.reference_period}</td>
                    {s.outputs.map((o) => (
                      <td key={o.horizon_years}>
                        {fmt(Number(o.debt_pct_gdp))}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty">
            Os cenários aparecerão após a ingestão da dívida e o processamento
            dos eventos.
          </p>
        )}
      </section>
      <DynamicSimulationSection initialBaseDebt={baseDebtValue} />
      <section>
        <div className="section-title">
          <h2>Revisão humana</h2>
          <span>PUBLICAÇÃO MATERIAL BLOQUEADA</span>
        </div>
        {alerts?.data.length ? (
          <ul className="alerts">
            {alerts.data.map((a) => (
              <li key={a.id}>
                <strong>
                  Impacto material: {fmt(Number(a.evidence.delta_pp))} p.p.
                </strong>
                <span>
                  Aguardando revisão humana · limiar experimental de 0,5 p.p.
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty">Nenhum alerta material registrado neste modo.</p>
        )}
      </section>
      <GovernanceAndObservabilitySection initialMetrics={observability?.data} />
      <MacroTrajectoryPanel initialTrajectories={trajectories?.data} />
      <PolicyLabPortfolio initialProposals={proposals?.data} />
      <GuidanceCommitmentsMatrix initialCommitments={guidance?.data} />
      <SourceFreshnessPanel initialSchedules={sourcesHealth?.data} />
      <InstitutionalMatrix
        institutions={
          institutions?.data && institutions.data.length > 0
            ? institutions.data
            : fallbackInstitutions
        }
      />
      <section>
        <h2>Cobertura do observatório</h2>
        <div className="domains">
          {catalog?.data.domains.map((d) => (
            <div key={d.id}>
              <span>{String(d.id).padStart(2, "0")}</span>
              {d.name}
              <small>
                {d.coverage === "pilot" ? "Piloto técnico" : "Planejado"}
              </small>
            </div>
          ))}
        </div>
      </section>
      <footer>
        Projeto independente. Não representa o governo brasileiro.
        <br />
        Constituição V1.3 · Guidance 2027–2030 experimental, sem metas
        aprovadas.
      </footer>
    </main>
  );
}
