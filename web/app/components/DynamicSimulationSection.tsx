"use client";

import { useState } from "react";

type AssumptionState = {
  interest: number; // in percent (e.g. 10.5)
  growth: number; // in percent (e.g. 4.5)
  primary: number; // in percent (e.g. 1.0)
  adjustment: number; // in percent (e.g. 0.0)
  horizonYears: number;
};

type TrajectoryPoint = {
  horizon_years: number;
  debt_pct_gdp: number;
};

export function DynamicSimulationSection({
  initialBaseDebt = 78.5,
}: {
  initialBaseDebt?: number;
}) {
  const [baseDebt, setBaseDebt] = useState<number>(initialBaseDebt);
  const [assumptions, setAssumptions] = useState<AssumptionState>({
    interest: 10.5,
    growth: 4.5,
    primary: 1.0,
    adjustment: 0.0,
    horizonYears: 4,
  });

  // Calculate deterministic fiscal path: d_t = (1 + i)/(1 + g) * d_{t-1} - p + a
  const calculatePath = (): TrajectoryPoint[] => {
    let d = baseDebt / 100;
    const i = assumptions.interest / 100;
    const g = assumptions.growth / 100;
    const p = assumptions.primary / 100;
    const a = assumptions.adjustment / 100;

    if (g <= -1) return [];

    const trajectory: TrajectoryPoint[] = [];
    for (let step = 1; step <= assumptions.horizonYears; step++) {
      d = ((1 + i) / (1 + g)) * d - p + a;
      trajectory.push({
        horizon_years: step,
        debt_pct_gdp: Math.round(d * 10000) / 100,
      });
    }
    return trajectory;
  };

  const trajectory = calculatePath();

  const fmt = (v: number) =>
    new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(v);

  return (
    <section aria-labelledby="dynamic-simulations" style={{ marginTop: "48px" }}>
      <div className="section-title">
        <h2 id="dynamic-simulations">Simulador Fiscal Dinâmico</h2>
        <span className="pill">PREMISSAS CUSTOMIZÁVEIS · CONDICIONAL</span>
      </div>

      <div className="notice" style={{ marginBottom: "24px" }}>
        <strong>AVISO METODOLÓGICO (Constituição V1.3):</strong>
        <p>
          Simulação contábil condicional baseada na identidade teórica da dívida bruta{" "}
          <code>d_t = [(1+i_t)/(1+g_t)] · d_(t-1) - p_t + a_t</code>. Não constitui previsão oficial,
          aconselhamento financeiro nem recomendação de política pública.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "24px",
          background: "white",
          border: "1px solid var(--line)",
          borderRadius: "16px",
          padding: "24px",
          marginBottom: "24px",
        }}
      >
        <div>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "8px" }}>
            Dívida Bruta Inicial: <strong>{fmt(baseDebt)}% do PIB</strong>
          </label>
          <input
            type="range"
            min="30"
            max="120"
            step="0.5"
            value={baseDebt}
            onChange={(e) => setBaseDebt(parseFloat(e.target.value))}
            style={{ width: "100%" }}
          />
        </div>

        <div>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "8px" }}>
            Juros Nominais Efetivos (i_t): <strong>{fmt(assumptions.interest)}% a.a.</strong>
          </label>
          <input
            type="range"
            min="0"
            max="25"
            step="0.25"
            value={assumptions.interest}
            onChange={(e) =>
              setAssumptions({ ...assumptions, interest: parseFloat(e.target.value) })
            }
            style={{ width: "100%" }}
          />
          <small style={{ color: "var(--muted)", display: "block", marginTop: "4px" }}>
            *Não equivale à taxa Selic diária bruta sem ponderação da carteira.
          </small>
        </div>

        <div>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "8px" }}>
            Crescimento Nominal do PIB (g_t): <strong>{fmt(assumptions.growth)}% a.a.</strong>
          </label>
          <input
            type="range"
            min="-5"
            max="20"
            step="0.25"
            value={assumptions.growth}
            onChange={(e) =>
              setAssumptions({ ...assumptions, growth: parseFloat(e.target.value) })
            }
            style={{ width: "100%" }}
          />
        </div>

        <div>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "8px" }}>
            Resultado Primário (p_t): <strong>{fmt(assumptions.primary)}% do PIB</strong>
          </label>
          <input
            type="range"
            min="-5"
            max="5"
            step="0.25"
            value={assumptions.primary}
            onChange={(e) =>
              setAssumptions({ ...assumptions, primary: parseFloat(e.target.value) })
            }
            style={{ width: "100%" }}
          />
          <small style={{ color: "var(--muted)", display: "block", marginTop: "4px" }}>
            Valores positivos representam superávit primário; negativos, déficit.
          </small>
        </div>

        <div>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "8px" }}>
            Ajuste Estoque-Fluxo (a_t): <strong>{fmt(assumptions.adjustment)}% do PIB</strong>
          </label>
          <input
            type="range"
            min="-3"
            max="3"
            step="0.1"
            value={assumptions.adjustment}
            onChange={(e) =>
              setAssumptions({ ...assumptions, adjustment: parseFloat(e.target.value) })
            }
            style={{ width: "100%" }}
          />
        </div>

        <div>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "8px" }}>
            Horizonte de Projeção: <strong>{assumptions.horizonYears} anos</strong>
          </label>
          <input
            type="range"
            min="1"
            max="10"
            step="1"
            value={assumptions.horizonYears}
            onChange={(e) =>
              setAssumptions({ ...assumptions, horizonYears: parseInt(e.target.value, 10) })
            }
            style={{ width: "100%" }}
          />
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <caption>Trajetória da Dívida Bruta (% do PIB) sob as premissas dinâmicas selecionadas</caption>
          <thead>
            <tr>
              <th scope="col">Período</th>
              <th scope="col">Ano Base</th>
              {trajectory.map((p) => (
                <th key={p.horizon_years} scope="col">
                  +{p.horizon_years} ano{p.horizon_years > 1 ? "s" : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">
                Cenário Customizado
                <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "4px" }}>
                  i={fmt(assumptions.interest)}% | g={fmt(assumptions.growth)}% | p={fmt(assumptions.primary)}%
                </div>
              </th>
              <td>{fmt(baseDebt)}%</td>
              {trajectory.map((p) => (
                <td key={p.horizon_years} style={{ fontWeight: 600 }}>
                  {fmt(p.debt_pct_gdp)}%
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}
