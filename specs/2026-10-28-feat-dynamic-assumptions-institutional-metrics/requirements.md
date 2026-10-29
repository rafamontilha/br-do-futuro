# Requirements — Dynamic Assumptions & Institutional Metrics

## Scope

**In scope:**
- Parametrização dinâmica da identidade fiscal da dívida bruta ($d_t = \frac{1+i_t}{1+g_t} d_{t-1} - p_t + a_t$):
  - Taxa de juros nominal efetiva anual da dívida ($i_t$);
  - Taxa de crescimento nominal anual do PIB ($g_t$);
  - Resultado primário em proporção do PIB ($p_t$);
  - Ajuste estoque-fluxo e esqueletos/reconhecimentos em proporção do PIB ($a_t$);
  - Horizonte de projeção ($T$ anos, default 4, entre 1 e 10 anos).
- Processamento assíncrono de simulações dinâmicas pelo Worker Python utilizando a fila transacional de eventos (`outbox` / `economic_events`).
- Mecanismo de notificação de conclusão da simulação (status `pending` → `completed` ou `failed`).
- Hash/Fingerprint SHA-256 das premissas para idempotência e reprodutibilidade de cálculo.
- Catálogo formal de atores institucionais mapeando competências constitucionais (`EXEC`, `LEG`, `JUD`, `BCB`, `TCU`, `SUB`, `SOC`).
- Mapeamento de papéis institucionais nos indicadores (`proposer`, `approver`, `executor`, `funder`, `auditor`, `beneficiary`).
- Exibição na UI (Next.js) de avisos metodológicos transparentes ("Simulação contábil condicional; não é previsão oficial nem conselho"), separando proponente de executor e exibindo a trajetória dinâmica simulada.

**Out of scope:**
- Previsão econométrica estocástica com vetores autorregressivos (VAR) ou modelos DSGE (mantém-se a identidade contábil simplificada).
- Uso da Selic diária bruta como juro anual da dívida sem deflator/ponderação metodológica.
- Publicação de recomendações ou guidance oficial automático (mantém-se como ferramenta analítica condicional).
- Integração de novas fontes externas de dados (ex: IBGE SIDRA direto fica para o Incremento de Fontes e Operação).

### Data / fields

#### Simulação Dinâmica (`dynamic_simulations` / `simulation_requests`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `simulation_id` | `VARCHAR(64)` | Sim | SHA-256 das premissas normalizadas |
| `base_debt_pct` | `NUMERIC(10,4)` | Sim | Dívida bruta inicial (% PIB), default: última observação disponível |
| `assumptions` | `JSONB` | Sim | Objeto contendo `interest`, `growth`, `primary`, `adjustment`, `horizon_years` |
| `status` | `VARCHAR(20)` | Sim | `pending`, `completed`, `failed` |
| `results` | `JSONB` | Não | Trajetória anualizada calculada `[{horizon_years, debt_pct_gdp}]` |
| `statement_type`| `VARCHAR(20)` | Sim | Sempre `projected` ou `hypothesis` |
| `requested_at` | `TIMESTAMPTZ` | Sim | Timestamp de criação |
| `completed_at` | `TIMESTAMPTZ` | Não | Timestamp de conclusão do processamento |

#### Atores Institucionais (`institutional_actors`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `actor_id` | `VARCHAR(32)` | Sim | Chave primária (`EXEC`, `LEG`, `JUD`, `BCB`, `TCU`, `SUB`, `SOC`) |
| `name` | `VARCHAR(128)` | Sim | Nome oficial da instituição/poder |
| `sphere` | `VARCHAR(32)` | Sim | `federal`, `subnational`, `independent`, `civil_society` |
| `legal_framework` | `TEXT` | Sim | Base legal de competência (CF/88, leis complementares) |
| `description` | `TEXT` | Sim | Descrição do papel no ordenamento econômico |

#### Papéis Institucionais por Indicador (`indicator_institutional_roles`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `indicator_id` | `VARCHAR(64)` | Sim | FK para `indicators` |
| `actor_id` | `VARCHAR(32)` | Sim | FK para `institutional_actors` |
| `role` | `VARCHAR(32)` | Sim | `proposer`, `approver`, `executor`, `funder`, `auditor`, `beneficiary` |
| `notes` | `TEXT` | Não | Detalhes sobre a atribuição legal no indicador |

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Execução de Simulações | Assíncrona via Worker Python + Outbox | Mantém a consistência com a arquitetura de eventos orientada a eventos (`tech-stack.md` e ADR 0014), sem sobrecarregar a API Go com processamento matemático pesado |
| Armazenamento | PostgreSQL append-only com status de processamento | Permite rastreabilidade temporal, evita perda de simulações solicitadas e garante reprodutibilidade via hash das premissas |
| Validação de Premissas | Validação estrita na API Go e no Worker Python | Rejeição imediata de valores infinitos, não numéricos ou bizarros ($g_t \le -100\%$, juros $< -50\%$) |
| Modelo de Governança | Mapeamento explícito das 7 competências de `specs/governance.md` | Evita atribuir ao Poder Executivo responsabilidades exclusivas do Congresso ou do Banco Central autônomo |
| Visualização e UX | Painel interativo com sliders, gráfico de trajetória e avisos metodológicos | Proporciona exploração ágil para pesquisadores com explicabilidade total de que se trata de simulação contábil hipotética |

## Context

- **Tone:** Analítico, independente, baseado em evidências e estritamente neutro, sem atribuir mérito ou demérito partidário (`specs/mission.md`).
- **Stack constraints:** Python 3.12+ para workers/regras matemáticas com tipos `Decimal`, Go 1.23+ para API de leitura e despacho de comandos, PostgreSQL 17 com schema append-only, Next.js 15+ com React 19 e Tailwind CSS (`specs/tech-stack.md`).
- **Existing patterns to follow:** Uso de transações seguras, isolamento entre dados de teste (`bdf_test`) e fixtures, rastreabilidade de linhagem e hashes SHA-256.
- **Open questions:** O tempo de retenção para simulações dinâmicas sob demanda de usuários anônimos (definido inicialmente como 30 dias com limpeza programada futura, se necessário).
