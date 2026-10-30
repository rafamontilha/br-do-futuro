# Requirements — Phase 1: Painéis de Realizado vs. Baseline, Forecast, Target e Cenário de Continuidade

## Scope

**In scope:**
- **Modelo de Trajetórias Macroeconômicas Unificadas:**
  - Consolidação temporal das 5 curvas comparativas para os 6 indicadores do núcleo P0:
    1. `br.ipca.12m` (Inflação IPCA acumulada 12 meses)
    2. `br.selic.target_annual` (Meta da Taxa Selic anualizada pelo Copom)
    3. `br.debt.gross_pct_gdp` (Dívida Bruta do Governo Geral % do PIB)
    4. `br.gdp.quarterly_yoy` (PIB a preços de mercado, variação % interanual)
    5. `br.fx.usd_brl.ptax` (Taxa de câmbio comercial USD/BRL fechamento PTAX)
    6. `br.labor.unemployment_rate` (Taxa de desocupação PNAD Contínua %)
  - As 5 curvas padronizadas por indicador:
    - **Realizado (`actual`):** Dados históricos capturados de fontes oficiais (BCB, IBGE, STN) com registro de vintage e hash SHA-256.
    - **Baseline (`baseline`):** Série histórica de referência / média histórica ou tendência pré-choque documentada.
    - **Forecast (`forecast`):** Projeção de modelos econométricos ou expectativas de mercado (marcada explicitamente como ilustrativa/em calibração até aprovação metodológica formal).
    - **Target (`target`):** Metas institucionais oficiais declaradas (ex.: meta de inflação do CMN, meta fiscal da LDO/Arcabouço, compromissos experimentais do Guidance).
    - **Cenário de Continuidade (`continuity`):** Projeção inercial 'sem novas medidas' com premissas de manutenção de regras vigentes.
- **Camada de Banco de Dados (PostgreSQL):**
  - Migração `db/007_trajectory_comparisons.sql` introduzindo tabela ou views materializadas de trajetórias de referência e calibração de horizontes (`target_series`, `forecast_series`, `baseline_series`).
  - Associação canônica com `indicators` e integridade referencial com períodos e vintages.
- **Camada de API (Go):**
  - Novo endpoint canônico `GET /v1/trajectories`:
    - Parâmetros de consulta: `indicator_id` (obrigatório ou filtro), `as_of` (corte bitemporal opcional), `start_period`, `end_period`.
    - Resposta estruturada contendo metadados do indicador, unidade, frequência, corte temporal e matriz unificada de períodos com os pontos correspondentes das 5 curvas e metadados de incerteza (banda inferior/superior para forecasts).
  - Testes unitários e de integração em `services/api/main_test.go`.
- **Interface Web (Next.js):**
  - Novo componente interativo `MacroTrajectoryPanel.tsx` no Observatório Econômico:
    - Seletor de indicador P0 (comutação entre as 6 séries).
    - Gráfico comparativo multi-curva vetorial (SVG/Canvas leve ou layout responsivo com visualização das 5 trajetórias e área sombreada de intervalo de confiança do forecast).
    - Badges semânticos de proveniência por curva: "Oficial", "Meta CMN / LDO", "Ilustrativo / Em Calibração", "Inercial".
    - Tabela de desvios e deltas (Realizado vs. Target, Realizado vs. Forecast, Realizado vs. Continuidade).
    - Seletor de data de corte `as_of` para simulação bitemporal da visão em momentos passados.

**Out of scope:**
- Algoritmo de backtesting dinâmico multi-horizonte (previsto para o item 4 da Fase 1).
- Workflow de intervenção e revisão humana de modelos via interface (item 3 da Fase 1).
- Séries setoriais ou regionais fora do núcleo P0 (previsto para a Fase 10).
- Publicação externa ou relatórios automáticos para download público.

### Data / fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `indicator_id` | string (VARCHAR 64) | Yes | Identificador canônico do indicador P0 |
| `period_date` | date (DATE) | Yes | Data de ancoragem do período (início do mês, trimestre ou dia) |
| `actual_value` | numeric (NUMERIC 16,6) | No | Valor realizado oficial verificado (nulo se período futuro) |
| `baseline_value` | numeric (NUMERIC 16,6) | No | Valor do baseline histórico de referência |
| `forecast_value` | numeric (NUMERIC 16,6) | No | Valor projetado pelo modelo ou mediana Focus |
| `forecast_lower` | numeric (NUMERIC 16,6) | No | Limite inferior da banda de incerteza do forecast |
| `forecast_upper` | numeric (NUMERIC 16,6) | No | Limite superior da banda de incerteza do forecast |
| `target_value` | numeric (NUMERIC 16,6) | No | Meta institucional oficial definida por lei ou resolução |
| `continuity_value` | numeric (NUMERIC 16,6) | No | Projeção inercial sem alteração de política pública |
| `actual_vintage` | timestamptz | No | Vintage de publicação oficial do dado realizado |
| `calibration_status` | string (VARCHAR 32) | Yes | Status de maturidade da projeção (`official`, `illustrative`, `preliminary`) |

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Endpoint Unificado | `GET /v1/trajectories` recebendo `indicator_id` | Evita N+1 chamadas desnecessárias no frontend, garante sincronização temporal atômica entre as 5 curvas e respeita o corte bitemporal `as_of` de forma centralizada |
| Normalização Temporal | Períodos ancorados no 1º dia da granularidade correspondente (`YYYY-MM-01`, `YYYY-01-01`) | Compatibiliza indicadores de frequências distintas (diário, mensal, trimestral) na mesma matriz de comparação anual/periódica |
| Badges e Disclaimers Visuais | Marcação explícita de "Ilustrativo / Não-oficial" em forecasts e cenários | Cumpre a Constituição do projeto (`specs/mission.md`), proibindo que previsões de modelo sejam confundidas com estatísticas oficiais |
| Tolerância a Lacunas | Campos anuláveis para períodos sem realizações (ex: anos futuros) ou sem meta fixada | Preserva a integridade da série temporal sem inventar interpolações espúrias |
| Gráfico Vetorial Limpo | SVG interativo nativo em React sem dependências pesadas externas | Mantém o bundle enxuto, compatibilidade total com Tailwind CSS e acessibilidade conforme diretrizes da stack |

## Context

- **Tone:** Neutro, auditável, rigoroso e baseado em evidências conforme `specs/mission.md`. Não qualificar variações como "boas" ou "más"; apresentar desvios puramente como grandezas numéricas acompanhadas de suas fontes e premissas.
- **Stack constraints:**
  - Python 3.12+ (Pydantic, testes de geração de trajetórias herméticas).
  - Go 1.22+ (pgx, standard library, rotas `/v1/trajectories`).
  - Next.js 14+ (App Router, React Server/Client Components, Tailwind CSS, TypeScript strict).
  - PostgreSQL 16+ (migrações em `db/`).
- **Existing patterns to follow:**
  - Migrações sequenciais em `db/007_*.sql`.
  - Endpoint de consulta em `services/api/main.go` e `services/api/repository.go`.
  - Componentes de painel modular em `web/app/components/`.
  - Tratamento bitemporal `as_of` herdado de `observations` e `guidance`.
- **Open questions:**
  - A periodicidade de atualização de forecasts será semanal (alinhada ao Focus) ou mensal?
    *Decisão provisória:* Mensal para compatibilidade com o fechamento macroeconômico, com granularidade trimestral para o PIB.
