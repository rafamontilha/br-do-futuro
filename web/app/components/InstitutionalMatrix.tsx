export type InstitutionalActor = {
  actor_id: string;
  name: string;
  sphere: string;
  legal_framework: string;
  description: string;
  indicator_roles?: {
    indicator_id: string;
    role: string;
    notes: string;
  }[];
};

const roleLabels: Record<string, string> = {
  proposer: "Proponente",
  approver: "Aprovador / Legislador",
  executor: "Executor / Gestor",
  funder: "Financiador",
  auditor: "Fiscalizador / Auditor",
  beneficiary: "Beneficiário",
};

const sphereLabels: Record<string, string> = {
  federal: "Federal",
  subnational: "Subnacional",
  independent: "Autônomo / Controle",
  civil_society: "Sociedade Civil",
};

export function InstitutionalMatrix({
  institutions = [],
}: {
  institutions?: InstitutionalActor[];
}) {
  return (
    <section aria-labelledby="institutional-governance" style={{ marginTop: "48px" }}>
      <div className="section-title">
        <h2 id="institutional-governance">Mapa de Competências Institucionais</h2>
        <span className="pill">SEPARAÇÃO DE PODERES · ART. 2º CF/88</span>
      </div>

      <p style={{ maxWidth: "800px", marginBottom: "24px" }}>
        Conforme a Constituição V1.3 do Brasil do Futuro, a discussão de políticas públicas distingue
        rigorosamente quem <strong>propõe</strong>, <strong>aprova</strong>, <strong>executa</strong>,{" "}
        <strong>financia</strong> e <strong>fiscaliza</strong> cada indicador e compromisso, evitando atribuir à
        esfera federal ou ao Poder Executivo responsabilidades exclusivas de outros poderes ou entes autônomos.
      </p>

      <div className="cards" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
        {institutions.map((actor) => (
          <article key={actor.actor_id} style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span className="eyebrow">{actor.actor_id}</span>
              <span className="tag">{sphereLabels[actor.sphere] || actor.sphere}</span>
            </div>

            <h3 style={{ margin: "8px 0" }}>{actor.name}</h3>
            <p style={{ fontSize: "14px", color: "var(--muted)", margin: "0 0 12px" }}>
              <strong>Base legal:</strong> {actor.legal_framework}
            </p>
            <p style={{ fontSize: "14px", flexGrow: 1, margin: 0 }}>{actor.description}</p>

            {actor.indicator_roles && actor.indicator_roles.length > 0 && (
              <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid var(--line)" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, letterSpacing: "0.5px" }}>
                  ATUAÇÃO NO CATÁLOGO PILOTO:
                </span>
                <ul style={{ paddingLeft: "18px", margin: "8px 0 0", fontSize: "13px" }}>
                  {actor.indicator_roles.map((r, idx) => (
                    <li key={idx} style={{ marginBottom: "4px" }}>
                      <strong>{r.indicator_id}</strong> —{" "}
                      <span className="tag" style={{ padding: "2px 6px", fontSize: "10px" }}>
                        {roleLabels[r.role] || r.role}
                      </span>
                      <div style={{ color: "var(--muted)", fontSize: "12px" }}>{r.notes}</div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
