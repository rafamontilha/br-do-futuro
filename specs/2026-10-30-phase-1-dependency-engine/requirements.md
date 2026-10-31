# Requirements — Phase 1: Motor de Dependências e Recálculo Seletivo; Workflow de Revisão Humana para Impactos Materiais

## Scope

**In scope:**
- **Grafo de Dependências Formal (DAG) e Recálculo Seletivo:**
  - Definição estruturada das dependências entre indicadores do núcleo P0 (`br.debt.gross_pct_gdp`, `br.ipca.12m`, `br.selic.target_annual`, `br.gdp.quarterly_yoy`, `br.fx.usd_brl.ptax`, `br.labor.unemployment_rate`), modelos econométricos/fiscais (`scenario_run`, `dynamic_simulations`), cenários analíticos e metas do Guidance institucional.
  - Motor de ordenação topológica e resolução de impactos no worker Python (`ingestion/bdf/dependency_engine.py`):
    - Ao receber `EconomicIndicatorUpdated` ou `HistoricalSeriesRevised`, o motor identifica os nós a jusante afetados.
    - Geração de plano explicável de recálculo seletivo (`recalculation_plan`) contendo nós a executar, justificativa causal e hashes de entrada, evitando recálculos redundantes de nós não afetados.
    - Emissão de eventos estruturados no outbox: `ScenarioRecalculationRequested`, `ScenarioRecalculated`, `ScenarioImpactDetected` e `MaterialReviewRequired`.
- **Regras Combinadas de Materialidade e Detecção de Impacto:**
  - Avaliação de dois eixos de materialidade configuráveis:
    1. **Variação absoluta projetada ($\Delta$ relevante):** $\ge 0,5$ p.p. na Dívida/PIB ou $\ge 0,25$ p.p. em inflação (IPCA) e taxas de juros (Selic).
    2. **Ruptura de meta institucional (`target breach`):** Quando a nova trajetória cruza ou se desvia do intervalo de tolerância da meta oficial do CMN ou do Arcabouço/LDO.
  - Disparo de alerta com severidade `material`, atribuição ao papel `Independent Reviewer`, SLA de 48 horas e bloqueio de publicação material até aprovação humana formal.
- **Workflow de Revisão Humana e Auditoria Imutável (Go API):**
  - Aprimoramento da tabela e dos endpoints de `alert`:
    - Novos campos em `alert`: `review_status` (`pending_human_review`, `approved`, `rejected`, `superseded`), `reviewed_by`, `review_justification`, `reviewed_at`.
    - Endpoint `POST /v1/alerts/{id}/review`: autenticado por chave de API (perfis `reviewer` ou `publisher`), exigindo justificativa obrigatória ($\ge 15$ caracteres) e gravando atomicamente na trilha imutável `decision_audit_log` com encadeamento de hashes SHA-256.
    - Endpoint `GET /v1/dependencies`: expõe o grafo canônico de dependências (nós, arestas, tipo de relação, periodicidade) para transparência e visualização.
    - Filtros avançados em `GET /v1/alerts`: filtro por `review_status`, `severity` e período.
- **Interface Web de Revisão e Governança (Next.js):**
  - Componente interativo `HumanReviewWorkflowModal.tsx` e painel `MaterialAlertsReviewPanel.tsx`:
    - Listagem de alertas materiais com visualização da evidência ($\Delta$ p.p., série afetada, ruptura de meta, SLA restante).
    - Formulário interativo para aprovar ou rejeitar o alerta, integrado ao seletor de perfil/API Key (`RoleSwitcherBadge`), com campo de justificativa obrigatório.
    - Visualizador interativo do Grafo de Dependências (DAG) ilustrando o fluxo: *Indicadores P0 → Modelos & Cenários → Metas do Guidance*.
    - Indicadores visuais claros de "Publicação Material Bloqueada" vs. "Aprovado por Revisor Independente".

**Out of scope:**
- Algoritmo de backtesting dinâmico multi-horizonte por vintage (previsto para o Item 4 da Fase 1).
- Integração de modelos de aprendizado de máquina adaptativos ou IA preditiva (previsto para Fase 10/100).
- Publicação externa de relatórios para o público geral sem intervenção humana.
- Alteração automática das metas oficiais do Guidance ou dos textos constitucionais.

### Data / fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `dependency_node_id` | string (VARCHAR 64) | Yes | Identificador único do nó do grafo (ex.: `indicator:br.debt.gross_pct_gdp`) |
| `dependency_node_type` | string (VARCHAR 32) | Yes | Tipo de nó (`indicator`, `model`, `scenario`, `guidance_target`) |
| `depends_on_node_id` | string (VARCHAR 64) | Yes | Identificador do nó a montante |
| `impact_relationship` | string (VARCHAR 32) | Yes | Natureza da relação (`direct_input`, `accounting_identity`, `behavioral_elasticity`) |
| `materiality_rule` | string (VARCHAR 64) | Yes | Identificador da regra de corte (ex.: `debt_delta_0_5pp`, `ipca_delta_0_25pp`) |
| `alert_id` | string (VARCHAR 64) | Yes | Identificador canônico do alerta de impacto material |
| `scenario_run_id` | string (VARCHAR 64) | Yes | Vínculo com a execução de cenário recalibrada |
| `severity` | string (VARCHAR 32) | Yes | Grau de severidade (`material`, `critical`, `informational`) |
| `review_status` | string (VARCHAR 32) | Yes | `pending_human_review`, `approved`, `rejected`, `superseded` |
| `reviewed_by` | string (VARCHAR 64) | No | Identificador do ator/revisor (`actor_id`) |
| `review_justification` | text | No | Justificativa técnica formal documentada |
| `reviewed_at` | timestamptz | No | Carimbo temporal da decisão humana |
| `sla_hours` | integer | Yes | SLA de revisão (padrão: 48 horas) |
| `evidence` | jsonb | Yes | Dicionário com `delta_pp`, `threshold_pp`, `rule`, `target_breach`, `event_id` |

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Estrutura do Grafo de Dependências** | DAG declarativo no PostgreSQL e processamento no Python worker | Garante persistência auditável das relações, permitindo inspeção via API e ordenação topológica sem dependências pesadas de bibliotecas de terceiros. |
| **Materialidade Multinível** | $\ge 0,5$ p.p. na Dívida/PIB ou $\ge 0,25$ p.p. em IPCA/Selic + Ruptura de Meta | Evita falsos positivos em pequenas oscilações conjunturais, ao mesmo tempo em que retém sensibilidade a desvios macroeconômicos estruturais e quebras de compromissos institucionais. |
| **Trilha de Decisão Imutável** | Gravação atômica em `decision_audit_log` via `POST /v1/alerts/{id}/review` | Cumpre o princípio constitucional de rastreabilidade e governança (ADR 0005/0014), vinculando a decisão a uma chave de API (`reviewer`/`publisher`) com hash criptográfico SHA-256 encadeado. |
| **Segregação de Papéis** | Somente perfis `reviewer` e `publisher` podem aprovar ou rejeitar revisões materiais | Impede que o produtor oficial do dado (`producer`) aprove o próprio impacto gerado por sua publicação sem validação independente. |
| **Experiência na UI Web** | Modal interativo com formulário de justificativa e visualização gráfica de dependências | Transforma a revisão humana em uma etapa operacional acessível e transparente, demonstrando no Observatório o estado de bloqueio e a governança em ação. |

## Context

- **Tone:** Alinhado a `specs/mission.md`: linguagem puramente descritiva, foco em evidências auditáveis, desvios expressos em grandezas percentuais sem rotulação partidária ou juízos morais.
- **Stack constraints:** Conforme `specs/tech-stack.md`: PostgreSQL 16+ com migrações sequenciais (`db/008_dependency_engine_and_reviews.sql`), worker Python com tipagem estrita, Go 1.22+ para a API REST e Next.js 15+ com React Server Components e Tailwind/CSS sem novas bibliotecas pesadas.
- **Existing patterns to follow:** Padrão das migrações 001–007, autenticação com `X-API-Key` implementada em `auth.go`, trilha de hash em `decision_audit_log` de `005_audit_logs_and_security.sql`.
- **Open questions:** Nenhuma — os 3 direcionamentos foram pactuados na entrevista (DAG formal abrangendo núcleo P0, painel interativo com audit log e regras combinadas de desvio/meta).
