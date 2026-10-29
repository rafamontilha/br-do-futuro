# Requirements — Method & Product: Public Proposals, Fiscal Calibration & Guidance Contracts (Incremento 03)

## Scope

**In scope:**
- **Carteira do Policy Lab com 3 Propostas Canônicas:**
  Modelagem estruturada de 3 propostas públicas de impacto econômico nacional:
  1. *Revisão e Eficiência do Gasto Obrigatório:* foco na sustentabilidade de despesas contínuas e previdenciárias, desindexação e regras de eficiência.
  2. *Aceleração do Investimento em Infraestrutura:* estímulo a parcerias público-privadas (PPP/PPI), marcos regulatórios e aumento da taxa de Formação Bruta de Capital Fixo (FBCF).
  3. *Simplificação Tributária e Produtividade:* neutralidade da carga, combate à cumulatividade, redução do Custo Brasil e desoneração de investimentos e exportações.
  Cada proposta conterá: hipótese causal explícita, estimativa de custo anual/plurianual, fonte de financiamento sustentável, competência institucional requerida (Executivo vs Legislativo/Emenda Constitucional), riscos, alternativas e evidências empíricas contrafactuais.
- **Tabelas Relacionais de Governança de Propostas e Guidance (`public_proposals`, `guidance_commitments`, `fiscal_calibrations`):**
  Estruturação de dados relacionais append-friendly no PostgreSQL com rastreabilidade de premissas, autorias institucionais e vínculos com séries econômicas canônicas.
- **Contratos de Guidance Brasil (2027–2030):**
  Separação explícita entre quatro dimensões fundamentais para cada compromisso:
  - `baseline`: valor de partida com período e vintage oficial comprovada.
  - `target`: meta quantitativa (sempre marcada como *proposta/hipotética* até validação humana formal).
  - `forecast`: projeção do modelo econômico com data de corte e identificador de cenário.
  - `actual`: dado realizado observado das fontes oficiais primárias (IBGE/BCB).
- **Calibração do Cenário Fiscal Base:**
  Parâmetros explícitos de elasticidade receita/PIB, custo médio da dívida pública e trajetória primária associados a cada proposta do Policy Lab.
- **API Go para Consulta de Propostas e Guidance:**
  - `GET /api/v1/proposals`: listagem de propostas com filtros por eixo e competência.
  - `GET /api/v1/proposals/{id}`: detalhamento com memória causal, riscos e financiamento.
  - `GET /api/v1/guidance/commitments`: matriz de compromissos comparando baseline, target, forecast e actual.
  - `GET /api/v1/scenarios/calibrations`: parâmetros fiscais calibrados vinculados às simulações.
- **Painéis Interativos no Next.js Dashboard:**
  - Seção **Policy Lab (Carteira de Propostas Públicas)** com visualização em cards detalhados, divisão de competências institucionais (Executivo vs Congresso) e impacto fiscal estimado.
  - Componente **Guidance Brasil (2027–2030)** com tabela de quatro quadrantes (Baseline | Meta Proposta | Projeção | Realizado) e badges de status metodológico.
  - Avisos e disclaimers obrigatórios de neutralidade, status "Hipotética / Em Avaliação" e ausência de vinculação estatal.

**Out of scope:**
- Ratificação automática de propostas ou declaração de aprovação de gates sem intervenção humana expressa.
- Automação da publicação de novas metas sem revisão metodológica independente.
- Preenchimento arbitrário ou sintético de metas oficiais como se fossem compromissos assumidos pelo Estado brasileiro.
- Execução orçamentária em tempo real ou simulações econométricas dinâmicas estocásticas gerais (DSGE complexo).
- Substituição da competência legal de órgãos governamentais ou formulação de políticas partidárias.

---

### Data / fields

#### Tabela `public_proposals`
| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `VARCHAR(64)` | Sim | Identificador canônico da proposta (PK, ex: `prop-fiscal-mandatory-spending`) |
| `title` | `VARCHAR(255)` | Sim | Título conciso da política pública |
| `policy_axis` | `VARCHAR(64)` | Sim | Eixo temático (`fiscal_quality`, `infrastructure_investment`, `tax_productivity`) |
| `status` | `VARCHAR(32)` | Sim | Status metodológico (`hypothesis_under_review`, `calibrated`, `ready_for_peer_review`) |
| `problem_statement` | `TEXT` | Sim | Diagnóstico e justificativa econômica da intervenção |
| `causal_mechanism` | `TEXT` | Sim | Hipótese causal ligando a medida aos resultados econômicos esperados |
| `cost_estimate_annual_brl` | `NUMERIC(14,2)`| Sim | Custo anual estimado em bilhões de reais (ou impacto fiscal líquido) |
| `cost_pct_gdp` | `NUMERIC(5,2)` | Não | Custo/impacto relativo percentual do PIB |
| `funding_source` | `TEXT` | Sim | Fonte real de financiamento e contrapartidas orçamentárias |
| `institutional_competence` | `VARCHAR(64)` | Sim | Competência institucional (`executive_decree`, `ordinary_law`, `constitutional_amendment`) |
| `responsible_actors` | `TEXT[]` | Sim | Órgãos envolvidos (ex: `["Ministério da Fazenda", "Congresso Nacional"]`) |
| `counterfactual_summary` | `TEXT` | Sim | Cenário contrafactual caso a política não seja implementada |
| `empirical_evidence` | `TEXT` | Sim | Estudos, referências históricas e literatura de suporte |
| `target_indicator_id` | `VARCHAR(64)` | Não | FK lógica para `economic_indicators.id` |
| `created_at` | `TIMESTAMPTZ` | Sim | Data de criação do registro |
| `updated_at` | `TIMESTAMPTZ` | Sim | Data da última alteração de premissas |

#### Tabela `guidance_commitments`
| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `VARCHAR(64)` | Sim | Identificador único do compromisso (PK, ex: `comm-investment-rate-2030`) |
| `proposal_id` | `VARCHAR(64)` | Não | FK para `public_proposals.id` quando vinculado a uma proposta específica |
| `indicator_id` | `VARCHAR(64)` | Sim | FK para `economic_indicators.id` |
| `name` | `VARCHAR(255)` | Sim | Descrição legível do compromisso plurianual |
| `horizon_year` | `INTEGER` | Sim | Ano horizonte do compromisso (ex: 2030) |
| `status` | `VARCHAR(32)` | Sim | Status (`experimental_hypothesis`, `proposed_target`, `under_evaluation`) |
| `baseline_period` | `VARCHAR(16)` | Sim | Período de referência inicial (ex: `2025-12`) |
| `baseline_value` | `NUMERIC(12,4)`| Sim | Valor inicial no período base |
| `target_value` | `NUMERIC(12,4)`| Sim | Meta quantitativa proposta para o horizonte |
| `forecast_value` | `NUMERIC(12,4)`| Não | Projeção do modelo de cenário de continuidade |
| `actual_latest_value`| `NUMERIC(12,4)`| Não | Último valor realizado oficial disponível na base |
| `unit` | `VARCHAR(32)` | Sim | Unidade de medida (ex: `% do PIB`, `% a.a.`) |
| `variance_explanation` | `TEXT` | Não | Análise qualitativa de desvio entre realizado e meta |
| `review_frequency` | `VARCHAR(32)` | Sim | Periodicidade de revisão (`annual`, `quarterly`) |
| `human_review_required` | `BOOLEAN` | Sim | Indica se qualquer alteração exige ratificação humana |
| `created_at` | `TIMESTAMPTZ` | Sim | Data de cadastro |
| `updated_at` | `TIMESTAMPTZ` | Sim | Data da última revisão |

#### Tabela `fiscal_calibrations`
| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `VARCHAR(64)` | Sim | Identificador da calibração (PK, ex: `calib-primary-surplus-v1`) |
| `scenario_id` | `VARCHAR(64)` | Sim | FK para cenário de simulação (`baseline`, `pessimistic`, `optimistic`) |
| `proposal_id` | `VARCHAR(64)` | Não | FK para `public_proposals.id` |
| `elasticity_revenue_gdp` | `NUMERIC(6,3)` | Sim | Elasticidade receita/PIB calibrada |
| `real_interest_rate_spread`| `NUMERIC(6,3)`| Sim | Spread de juros reais da dívida em p.p. |
| `primary_balance_shift_pct_gdp` | `NUMERIC(6,3)` | Sim | Choque fiscal primário acumulado (% PIB) |
| `notes` | `TEXT` | Sim | Justificativa técnica da calibração |
| `created_at` | `TIMESTAMPTZ` | Sim | Data de calibração |

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Modelo de Propostas Públicas** | 3 propostas canônicas no Policy Lab (Gasto Obrigatório, Infraestrutura, Tributária) | Atende com exatidão ao critério exigido no Gate 0→1 da Fundação ("três propostas com custo, mecanismo, competência e cenários"), cobrindo os eixos estruturantes sem inventar promessas governamentais fictícias. |
| **Persistência de Dados Relacional** | Tabelas dedicadas `public_proposals`, `guidance_commitments` e `fiscal_calibrations` no PostgreSQL | Evita acoplamento prematuro em arquivos estáticos e permite que a API Go forneça consultas rápidas com junção e integridade referencial com os indicadores já mapeados (`br.ipca.monthly`, `br.debt.gross_pct_gdp`, etc.). |
| **Contratos de Guidance com 4 Quadrantes** | Separação explícita de `baseline`, `target`, `forecast` e `actual` | Implementa a regra constitucional de que novas vintages e divulgações observadas nunca sobrescrevem metas históricas assumidas, preservando a memória e a explicabilidade dos desvios. |
| **Governança de Metas e Propostas** | Rotulagem explícita `experimental_hypothesis` e bloqueio de ratificação automática | Em conformidade direta com a Constituição de `specs/mission.md`, `specs/governance.md` e a regra do usuário, o sistema não pode publicar recomendações ou marcar gates como concluídos sem validação humana documental. |
| **Apresentação e UX** | Cards no Policy Lab com distinção de Poder (Executivo vs Legislativo) + Painel Guidance 2027-2030 | Torna didática e acessível a separação de competências institucionais do Estado brasileiro, evitando a presunção errônea de que o Poder Executivo pode alterar regras tributárias ou orçamentárias sem aprovação parlamentar. |

---

## Context

- **Tone:** Estritamente neutro, técnico, apartidário e fundamentado em evidências e limites legais de competência (conforme `specs/mission.md` e `specs/governance.md`).
- **Stack constraints:** Python 3.12+ para validação e cálculos econométricos de calibração, PostgreSQL 16 para esquema relacional e transações auditáveis, Go 1.22+ para endpoints HTTP REST com tipagem forte e testes de integração, Next.js 16 (App Router) + Tailwind CSS para renderização de interface responsiva e acessível.
- **Existing patterns to follow:**
  - Migrações numeradas em `db/` (`004_proposals_and_guidance.sql`).
  - IDs canônicos em kebab-case com prefixo (`prop-*`, `comm-*`, `calib-*`).
  - Tratamento de unidades econômicas corretas (diferenças percentuais em pontos percentuais, não variação relativa).
  - Testes automatizados cobrindo schemas, rejeição de payloads inválidos e integridade referencial.
- **Open questions:**
  - Definição do responsável humano independente para ratificação formal da revisão metodológica (marcado no banco como `TO_BE_ASSIGNED_BY_GOVERNANCE`).
  - Integração futura dos impactos das 3 propostas diretamente na fórmula de evolução dinâmica da dívida bruta no worker Python.
